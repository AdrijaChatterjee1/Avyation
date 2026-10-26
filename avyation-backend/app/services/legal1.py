"""POST /api/calculate-payout: jurisdiction matching + entitlement maths + legal notice.

Several regimes can apply to one flight (e.g. Air France DEL->CDG falls under both DGCA and EU261).
We compute every applicable regime and surface the most valuable one as `primary`; passengers
cannot double-dip, so the others are returned as `alternatives`.

!! VERIFY BEFORE DEMO / PRODUCTION !!
 * DGCA thresholds below follow the Avyation product spec (cash tiers INR 5,000 / 7,500 / 10,000
   by block time, applied at 3h+ delay). The official CAR Section 3 Series M Part IV pays cash
   mainly for cancellations / denied boarding, and gives refund / re-routing options for long
   delays. Confirm the current CAR text and adjust DGCA_CASH_DELAY_MIN if needed.
 * FX_TO_INR is an approximate constant used ONLY to rank regimes; it never appears in output.
 * This is information, not legal advice.
"""
import math
from typing import Optional

from ..models import AuditResult, FlightRef, PayoutResult
from ..store import AIRPORTS, CARRIERS, airline_name
from .llm import gemini_text

FX_TO_INR = {"INR": 1.0, "EUR": 90.0, "GBP": 105.0, "USD": 84.0}
SYMBOL = {"INR": "₹", "EUR": "€", "GBP": "£", "USD": "$"}

EU_EEA = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
    "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "NO", "CH",
}

DGCA_CASH_DELAY_MIN = 180
DGCA_MEALS_DELAY_MIN = 120
DGCA_HOTEL_DELAY_MIN = 360


def money(amount: float, currency: str) -> str:
    return f"{SYMBOL.get(currency, currency + ' ')}{amount:,.0f}"


def country_of(iata: str) -> Optional[str]:
    return AIRPORTS.get(iata, {}).get("country")


def distance_km(a: str, b: str) -> float:
    pa, pb = AIRPORTS[a], AIRPORTS[b]
    lat1, lon1, lat2, lon2 = map(math.radians, (pa["lat"], pa["lon"], pb["lat"], pb["lon"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _finish(r: PayoutResult) -> PayoutResult:
    if r.cash_amount is None:
        r.display_amount = "Refund of ticket price" if r.eligible else ""
    elif not r.eligible:
        r.display_amount = "No cash compensation"
    else:
        r.display_amount = money(r.cash_amount, r.currency)
    return r


# ------------------------------------------------------------------ regimes
def _eu_style(name: str, citation: str, tiers: tuple, currency: str, flight: dict,
              delay: int, cancelled: bool, extraordinary: bool) -> PayoutResult:
    dist = distance_km(flight["origin"], flight["destination"])
    amount = tiers[0] if dist <= 1500 else tiers[1] if dist <= 3500 else tiers[2]
    reasoning = [f"Great-circle distance ≈ {dist:,.0f} km → base compensation {money(amount, currency)}."]
    if not cancelled and delay < 240 and dist > 3500:
        amount = amount / 2
        reasoning.append("Arrival delay under 4h on a 3,500 km+ flight → 50% reduction applies.")
    care_after = 120 if dist <= 1500 else 180 if dist <= 3500 else 240
    entitlements = []
    if cancelled or delay >= care_after:
        entitlements += ["Meals and refreshments", "Two phone calls / emails"]
    if cancelled or delay >= 480:
        entitlements.append("Hotel accommodation + transfers if an overnight stay is needed")

    meets = cancelled or delay >= 180
    eligible = meets and not extraordinary
    if not meets:
        reasoning.append(f"Arrival delay of {delay} min is under the 3h threshold.")
    elif extraordinary:
        reasoning.append("Airline's extraordinary-circumstances defence looks valid; cash compensation is not owed (care duties still apply).")
    else:
        reasoning.append("Delay/cancellation is within the airline's control → cash compensation owed.")
    return PayoutResult(
        regime=name, citation=citation, applicable=True, eligible=eligible,
        cash_amount=amount if eligible else 0.0, currency=currency,
        entitlements=entitlements, reasoning=reasoning,
        caveats=["Cancellations with 14+ days' notice are not compensable; confirm notice date."] if cancelled else [],
    )


def _dgca(flight: dict, delay: int, cancelled: bool, extraordinary: bool,
          base_fare: Optional[float]) -> PayoutResult:
    block = flight.get("block_minutes", 120)
    tier = 5000.0 if block <= 60 else 7500.0 if block <= 120 else 10000.0
    reasoning = [f"Block time {block} min → compensation tier ₹{tier:,.0f}."]
    amount = tier
    if base_fare:
        amount = min(tier, base_fare)
        if amount < tier:
            reasoning.append(f"Capped at the basic fare (₹{base_fare:,.0f}).")
    entitlements = []
    if cancelled or delay >= DGCA_MEALS_DELAY_MIN:
        entitlements.append("Meals and refreshments")
    if cancelled or delay >= DGCA_HOTEL_DELAY_MIN:
        entitlements.append("Hotel accommodation + transfers (overnight / 6h+ disruption)")
    meets = cancelled or delay >= DGCA_CASH_DELAY_MIN
    eligible = meets and not extraordinary
    if not meets:
        reasoning.append(f"Delay of {delay} min is under the {DGCA_CASH_DELAY_MIN // 60}h cash threshold; care entitlements only.")
    elif extraordinary:
        reasoning.append("Extraordinary circumstances appear valid; cash compensation not owed.")
    else:
        reasoning.append("Cause is within the airline's control → compensation owed.")
    return PayoutResult(
        regime="DGCA CAR Section 3, Series M, Part IV",
        citation="DGCA Civil Aviation Requirements, Section 3, Series M, Part IV (Passenger Charter)",
        applicable=True, eligible=eligible, cash_amount=amount if eligible else 0.0, currency="INR",
        entitlements=entitlements, reasoning=reasoning,
        caveats=["Cash tier for delays follows the Avyation product spec; confirm against the current CAR text."],
    )


def _us_dot(flight: dict, delay: int, cancelled: bool, base_fare: Optional[float]) -> PayoutResult:
    domestic = country_of(flight["origin"]) == "US" and country_of(flight["destination"]) == "US"
    threshold = 180 if domestic else 360
    eligible = cancelled or delay >= threshold
    reasoning = [
        f"Refund triggers: cancellation, or {'domestic 3h+' if domestic else 'international 6h+'} delay "
        f"(this flight: {'cancelled' if cancelled else f'{delay} min'})."
    ]
    return PayoutResult(
        regime="US DOT 14 CFR Part 260 (automatic refunds)",
        citation="US DOT automatic refund rule, 14 CFR Part 260",
        applicable=True, eligible=eligible,
        cash_amount=base_fare if (eligible and base_fare) else None, currency="USD",
        entitlements=["Full refund to original payment method"] if eligible else [],
        reasoning=reasoning,
        caveats=["US rules give refunds, not EU-style fixed compensation, for delays."],
    )


def applicable_regimes(flight: dict) -> list[str]:
    dep, arr = country_of(flight["origin"]), country_of(flight["destination"])
    carrier = CARRIERS.get(flight["airline_code"], {}).get("country")
    regimes = []
    if dep == "IN":
        regimes.append("DGCA")
    if dep in EU_EEA or (arr in EU_EEA and carrier in EU_EEA):
        regimes.append("EU261")
    if dep == "GB" or (arr == "GB" and carrier == "GB"):
        regimes.append("UK261")
    if "US" in (dep, arr):
        regimes.append("USDOT")
    return regimes


def compute_payout(flight: dict, ref: FlightRef, audit: Optional[AuditResult],
                   delay_minutes: Optional[int] = None, cancelled: Optional[bool] = None,
                   extraordinary: Optional[bool] = None) -> tuple[PayoutResult, list[PayoutResult]]:
    delay = int(flight["arrival_delay_minutes"]) if delay_minutes is None else delay_minutes
    cancel = bool(flight["cancelled"]) if cancelled is None else cancelled
    extra = (audit.extraordinary_circumstances_valid if audit else False) if extraordinary is None else extraordinary

    results: list[PayoutResult] = []
    for regime in applicable_regimes(flight):
        if regime == "DGCA":
            results.append(_dgca(flight, delay, cancel, extra, ref.base_fare))
        elif regime == "EU261":
            results.append(_eu_style("EU261 (Regulation EC 261/2004)", "Regulation (EC) No 261/2004, Articles 5 and 7",
                                     (250, 400, 600), "EUR", flight, delay, cancel, extra))
        elif regime == "UK261":
            results.append(_eu_style("UK261 (retained EC 261/2004)", "Air Passenger Rights and Air Travel Organisers' Licensing (Amendment) (EU Exit) Regulations 2019",
                                     (220, 350, 520), "GBP", flight, delay, cancel, extra))
        elif regime == "USDOT":
            results.append(_us_dot(flight, delay, cancel, ref.base_fare))
    for r in results:
        _finish(r)

    if not results:
        none = PayoutResult(regime="No supported regime", citation="n/a", applicable=False, eligible=False,
                            reasoning=["No supported passenger-rights regime matches this route and carrier."])
        return none, []

    def value(r: PayoutResult) -> float:
        return (r.cash_amount or 0.0) * FX_TO_INR.get(r.currency, 1.0)

    results.sort(key=lambda r: (r.eligible, value(r)), reverse=True)
    return results[0], results[1:]


# ------------------------------------------------------------------ notice
def build_notice(flight: dict, ref: FlightRef, audit: AuditResult, primary: PayoutResult) -> str:
    who = ref.passenger_name or "the undersigned passenger"
    amount = primary.display_amount if primary.eligible and primary.display_amount else "the care entitlements set out below"
    problem = "was cancelled" if audit.cancelled else f"arrived {audit.delay_minutes // 60}h {audit.delay_minutes % 60}m late"
    lines = [
        f"Subject: Statutory compensation claim - flight {flight['flight_number']} on {ref.date or flight['date']} (PNR {ref.pnr or 'on file'})",
        "",
        f"To the Customer Relations / Grievance Officer, {airline_name(flight['airline_code'])},",
        "",
        f"I, {who}, was booked on flight {flight['flight_number']} ({audit.route}) scheduled for "
        f"{flight['scheduled_departure']} on {ref.date or flight['date']}. The flight {problem}.",
        f"The reason given was: \"{audit.stated_reason}\".",
        "",
        "Independent review of the available data shows:",
    ]
    lines += [f"  - {e.label}: {e.detail}" for e in audit.evidence]
    lines += [
        "",
        f"Under {primary.citation}, I am entitled to {amount}.",
    ]
    if primary.entitlements:
        lines.append("Please also reimburse or provide: " + "; ".join(primary.entitlements) + ".")
    lines += [
        "",
        "Please confirm payment within 14 days of this notice. If the claim is rejected, please state the "
        "specific legal basis and supporting evidence; I will otherwise escalate to the relevant "
        "aviation authority (DGCA AirSewa / National Enforcement Body) and pursue my statutory remedies.",
        "",
        f"Regards,\n{who}",
    ]
    return "\n".join(lines)


async def polish_notice(draft: str) -> str:
    """Optional LLM polish; keeps every fact, falls back to the template draft."""
    out = await gemini_text(
        "Polish this passenger-rights demand letter. Keep it firm, polite and concise. "
        "Do NOT change any fact, amount, date, name, number or legal citation, and add nothing new. "
        "Return only the letter text.\n\n" + draft
    )
    return out.strip() if out else draft
