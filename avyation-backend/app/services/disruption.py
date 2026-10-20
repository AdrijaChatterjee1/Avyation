"""POST /api/audit-disruption: cross-check the airline's stated delay reason against live data.

'Excuse-Buster' logic: weather is only a valid extraordinary circumstance if conditions at the
airport were actually severe AND other flights in the same window were disrupted too.
Technical / crew / late-inbound reasons are the airline's own responsibility.
"""
import re
from typing import Optional

from ..config import settings
from ..models import AuditResult, EvidenceItem
from ..store import AIRPORTS
from .tinyfish import TinyFishError, tinyfish

REASON_KEYWORDS = [
    ("weather", ("weather", "fog", "visibility", "storm", "thunder", "rain", "cyclone", "wind")),
    ("atc", ("atc", "air traffic", "airspace", "slot", "congestion")),
    ("security", ("security", "bomb", "terror")),
    ("technical", ("technical", "maintenance", "aircraft fault", "engineering", "snag")),
    ("crew", ("crew", "pilot", "duty time", "staff")),
    ("operational", ("operational", "late arrival", "inbound", "rotation", "schedule")),
]
# Categories that can legitimately qualify as "extraordinary circumstances".
EXTRAORDINARY_CATEGORIES = {"weather", "atc", "security"}

COMPENSABLE_DELAY_MIN = 120  # below this there is nothing meaningful to claim


def categorize(reason: str) -> str:
    low = reason.lower()
    for category, words in REASON_KEYWORDS:
        if any(re.search(rf"\b{re.escape(w)}", low) for w in words):
            return category
    return "other"


def parse_metar(raw: str) -> dict:
    """Pull visibility (m) and thunderstorm flag out of a raw METAR string."""
    tokens = raw.split()
    vis_m = 9999
    if "CAVOK" in tokens:
        vis_m = 10000
    else:
        seen_wind = False
        for tok in tokens:
            if re.match(r"^\d{3}\d{2,3}(G\d{2,3})?(KT|MPS)$", tok) or tok.startswith("VRB"):
                seen_wind = True
                continue
            m_sm = re.match(r"^(\d+)SM$", tok)
            if m_sm:
                vis_m = int(int(m_sm.group(1)) * 1609)
                break
            if seen_wind and re.match(r"^\d{4}$", tok):
                vis_m = int(tok)
                break
    thunder = any("TS" in t for t in tokens[2:])
    fog = any(t.endswith("FG") or t == "FG" for t in tokens)
    if thunder:
        cond = f"Thunderstorm, visibility {vis_m} m"
    elif fog or vis_m < 1000:
        cond = f"Fog / low visibility, {vis_m} m"
    else:
        cond = f"No significant weather, visibility {vis_m} m"
    return {"raw": raw, "visibility_m": vis_m, "thunderstorm": thunder, "conditions": cond}


async def fetch_live_weather(icao: str) -> Optional[dict]:
    """Ask the TinyFish web agent to read the latest METAR. Returns None on any failure so the
    audit falls back to the bundled demo observation."""
    if not (tinyfish.enabled and settings.live_weather):
        return None
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw&hours=3"
    goal = (
        f"Read this page and return JSON of the form {{\"metar\": \"<most recent raw METAR line "
        f"for {icao}>\"}}. Do not click anything or leave the page."
    )
    try:
        result = await tinyfish.run(url, goal, timeout=120)
    except TinyFishError:
        return None
    raw = result.get("metar") if isinstance(result, dict) else str(result)
    return parse_metar(raw) if raw else None


def audit_flight(flight: dict, weather_override: Optional[dict] = None) -> AuditResult:
    stated = flight.get("airline_stated_reason", "No reason given")
    category = categorize(stated)
    delay = int(flight.get("arrival_delay_minutes", 0))
    cancelled = bool(flight.get("cancelled"))
    weather = weather_override or flight["weather"]
    live = weather_override is not None
    src = "aviationweather.gov via TinyFish (live)" if live else "Avyation demo dataset"
    icao = AIRPORTS.get(flight["origin"], {}).get("icao", flight["origin"])

    other = flight["other_departures"]
    on_time, total = other["departed_on_time"], other["total"]
    ratio = on_time / total if total else 0.0

    evidence: list[EvidenceItem] = [
        EvidenceItem(label=f"METAR {icao}", detail=f"{weather['raw']} -> {weather['conditions']}"),
    ]
    valid = False

    if category == "weather":
        severe = weather["thunderstorm"] or weather["visibility_m"] < 800
        others_disrupted = ratio < 0.5
        evidence.append(EvidenceItem(
            label="Observed weather",
            detail=("Severe conditions confirmed" if severe else "Conditions were operationally normal"),
            supports_claim=not severe))
        evidence.append(EvidenceItem(
            label="Other departures",
            detail=f"{on_time} of {total} flights left on time within {other['window_minutes']} min of this one",
            supports_claim=not others_disrupted))
        valid = severe and others_disrupted
    elif category in EXTRAORDINARY_CATEGORIES:
        valid = True
        evidence.append(EvidenceItem(
            label="Stated reason",
            detail=f"'{stated}' is normally an extraordinary circumstance; verify against NOTAMs/ATC records",
            supports_claim=False))
    else:
        evidence.append(EvidenceItem(
            label="Stated reason",
            detail=f"'{stated}' is within the airline's control and is not an extraordinary circumstance",
            supports_claim=True))

    delayed_enough = cancelled or delay >= COMPENSABLE_DELAY_MIN
    at_fault = delayed_enough and not valid

    if not delayed_enough:
        verdict = f"Delay of {delay} min is below compensation thresholds; only care entitlements may apply."
    elif category == "weather" and not valid:
        verdict = f"Weather excuse disproved: {on_time} other flights departed normally."
    elif valid:
        verdict = "Airline's excuse looks valid (extraordinary circumstances); cash compensation is unlikely."
    else:
        verdict = f"Airline-controllable cause ({category}); compensation claim is supported."

    return AuditResult(
        flight_number=flight["flight_number"],
        route=f"{flight['origin']} → {flight['destination']}",
        stated_reason=stated, reason_category=category, delay_minutes=delay, cancelled=cancelled,
        extraordinary_circumstances_valid=valid, airline_at_fault=at_fault,
        verdict=verdict, evidence=evidence, data_source=src,
    )
