"""Rule-based passenger-rights assessment for Avyation's simulated flight scenarios.

The flight facts are demo inputs. This module applies conservative rule checks and
returns a simulated assessment; it does not verify real flight operations or provide
legal advice. Missing facts are surfaced as caveats instead of silently assumed.

Official rule references checked 2026-10-26:
- India: DGCA CAR Section 3, Series M, Part IV (Passenger Charter)
- EU: Regulation (EC) 261/2004 and official Your Europe passenger-rights guidance
- US: 14 CFR Part 260 / US DOT refund guidance

UK261 amounts and detailed eligibility can change; verify the current UK CAA guidance
before production use. This prototype intentionally does not treat an ordinary delay
on an India-only itinerary as an automatic fixed-cash compensation award.
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

# EU261 care thresholds are based on departure delay and distance. We only have
# departure delay in the bundled scenarios, so use that field for assistance.
def money(amount: float, currency: str) -> str:
    return f"{SYMBOL.get(currency, currency + ' ')}{amount:,.0f}"


def country_of(iata: str) -> Optional[str]:
    return AIRPORTS.get(iata, {}).get("country")


def distance_km(a: str, b: str) -> float:
    pa, pb = AIRPORTS[a], AIRPORTS[b]
    lat1, lon1, lat2, lon2 = map(math.radians, (pa["lat"], pa["lon"], pb["lat"], pb["lon"]))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2 * 6371.0 * math.asin(math.sqrt(min(1.0, h)))


def _finish(r: PayoutResult) -> PayoutResult:
    if r.cash_amount is None:
        r.display_amount = "Refund of ticket price (amount requires fare data)" if r.eligible else ""
    elif not r.eligible:
        r.display_amount = "No fixed cash compensation established"
    else:
        r.display_amount = money(r.cash_amount, r.currency)
    return r


def _eu261(flight: dict, delay: int, cancelled: bool, extraordinary: bool) -> PayoutResult:
    dist = distance_km(flight["origin"], flight["destination"])
    if dist <= 1500:
        amount = 250.0
        care_threshold = 120
        tier = "≤1,500 km"
    elif dist <= 3500:
        amount = 400.0
        care_threshold = 180
        tier = "1,500–3,500 km"
    else:
        amount = 600.0
        care_threshold = 240
        tier = ">3,500 km"
        if not cancelled and 180 <= delay < 240:
            amount = 300.0

    dep, arr = country_of(flight["origin"]), country_of(flight["destination"])
    carrier = CARRIERS.get(flight.get("airline_code", ""), {}).get("country")
    # EU261 compensation requires a covered itinerary and the applicable conditions.
    applicable = dep in EU_EEA or (arr in EU_EEA and carrier in EU_EEA)
    reasoning = [f"Great-circle distance ≈ {dist:,.0f} km ({tier})."]
    entitlements = []
    dep_delay = int(flight.get("departure_delay_minutes", delay))
    if cancelled or dep_delay >= care_threshold:
        entitlements.extend(["Meals and refreshments appropriate to the waiting time", "Two calls, emails or equivalent communications"])
    if cancelled or flight.get("overnight_stay_needed", False):
        entitlements.append("Hotel accommodation and airport transfers if an overnight stay is necessary")

    if not applicable:
        eligible = False
        reasoning.append("The itinerary/carrier combination does not match the supported EU261 scope.")
    elif extraordinary:
        eligible = False
        reasoning.append("Scenario audit treats extraordinary circumstances as established; fixed compensation is not indicated, though care duties may remain.")
    elif cancelled:
        notice_hours = flight.get("cancellation_notice_hours_before_departure")
        reroute = flight.get("alternative_offered")
        if notice_hours is None or reroute is None:
            eligible = False
            reasoning.append("Cancellation compensation cannot be confirmed: cancellation-notice timing and rerouting details are missing.")
        elif notice_hours >= 336:
            eligible = False
            reasoning.append("Scenario says the passenger was notified at least 14 days before departure; EU261 cancellation compensation is not indicated.")
        else:
            eligible = True
            reasoning.append("Scenario says notice was under 14 days; assess the offered rerouting/arrival-time conditions before treating compensation as final.")
    elif delay >= 180:
        eligible = True
        reasoning.append("Scenario arrival delay is at least 3 hours and the audit did not establish extraordinary circumstances.")
    else:
        eligible = False
        reasoning.append("Arrival delay is below the 3-hour compensation threshold.")

    caveats = ["Demo scenario only. For cancellations, verify the notice date and any rerouting/arrival-time conditions before confirming compensation."]
    if not applicable:
        caveats.append("EU261 scope depends on departure airport or arrival in the EU on an EU carrier.")
    return PayoutResult(
        regime="EU261 (Regulation EC 261/2004)",
        citation="Regulation (EC) No 261/2004, Articles 5, 6, 7, 8 and 9; official Your Europe air passenger rights guidance",
        applicable=applicable, eligible=eligible, cash_amount=amount if eligible else 0.0, currency="EUR",
        entitlements=entitlements, reasoning=reasoning, caveats=caveats,
    )


def _uk261(flight: dict, delay: int, cancelled: bool, extraordinary: bool) -> PayoutResult:
    dist = distance_km(flight["origin"], flight["destination"])
    if dist <= 1500:
        amount, care_threshold = 220.0, 120
    elif dist <= 3500:
        amount, care_threshold = 350.0, 180
    else:
        amount, care_threshold = 520.0, 240
        if not cancelled and 180 <= delay < 240:
            amount = 260.0
    dep, arr = country_of(flight["origin"]), country_of(flight["destination"])
    carrier = CARRIERS.get(flight.get("airline_code", ""), {}).get("country")
    applicable = dep == "GB" or (arr == "GB" and carrier == "GB")
    entitlements = []
    if cancelled or int(flight.get("departure_delay_minutes", delay)) >= care_threshold:
        entitlements.extend(["Meals and refreshments appropriate to the waiting time", "Communications"])
    if cancelled or flight.get("overnight_stay_needed", False):
        entitlements.append("Hotel accommodation and transfers if required")
    eligible = applicable and not extraordinary and (delay >= 180 or cancelled)
    reasoning = [f"Great-circle distance ≈ {dist:,.0f} km."]
    if not applicable:
        reasoning.append("The itinerary/carrier combination does not match the supported UK261 scope.")
    elif extraordinary:
        reasoning.append("Scenario audit treats extraordinary circumstances as established; fixed compensation is not indicated.")
    elif cancelled:
        notice = flight.get("cancellation_notice_hours_before_departure")
        if notice is None:
            eligible = False
            reasoning.append("Cancellation notice timing is missing; compensation cannot be confirmed.")
        elif notice >= 336:
            eligible = False
            reasoning.append("Scenario says notice was at least 14 days before departure.")
        else:
            reasoning.append("Scenario says notice was under 14 days; verify rerouting conditions before confirming.")
    elif delay < 180:
        reasoning.append("Arrival delay is below the 3-hour threshold.")
    else:
        reasoning.append("Arrival delay meets the 3-hour threshold and extraordinary circumstances were not established.")
    return PayoutResult(
        regime="UK261", citation="UK retained air passenger rights rules; verify current UK CAA guidance",
        applicable=applicable, eligible=eligible, cash_amount=amount if eligible else 0.0, currency="GBP",
        entitlements=entitlements, reasoning=reasoning,
        caveats=["Prototype UK compensation bands; verify current UK CAA rules and cancellation/rerouting facts before production use."],
    )


def _dgca(flight: dict, delay: int, cancelled: bool, extraordinary: bool) -> PayoutResult:
    block = int(flight.get("block_minutes", 120))
    dep_delay = int(flight.get("departure_delay_minutes", delay))
    entitlements = []
    # DGCA CAR has assistance/refund/re-routing provisions; do not invent a fixed
    # cash amount for a normal delayed flight.
    if cancelled or (block <= 150 and dep_delay >= 120) or (block > 150 and dep_delay >= 180):
        entitlements.append("Meals and refreshments, subject to the applicable DGCA CAR conditions")
    if cancelled or flight.get("overnight_stay_needed", False):
        entitlements.append("Hotel accommodation and transfers where required by the applicable DGCA CAR conditions")
    if not cancelled and dep_delay >= 360:
        entitlements.append("Assess refund or alternative-flight options for a delay of 6 hours or more")

    eligible = False
    amount = 0.0
    reasoning = [f"Scheduled block time: {block} minutes; departure delay: {dep_delay} minutes; arrival delay: {delay} minutes."]
    caveats = ["DGCA CAR does not establish a universal ₹5,000/₹7,500/₹10,000 cash award for every long delay. This engine therefore does not award fixed cash for delay alone."]
    if cancelled:
        notice = flight.get("cancellation_notice_hours_before_departure")
        alternative = flight.get("alternative_offered")
        if extraordinary:
            reasoning.append("The scenario audit treats extraordinary circumstances as established; cash compensation is not indicated.")
        elif notice is None or alternative is None:
            reasoning.append("Cancellation compensation cannot be determined without notice timing and alternative-flight/refund facts.")
            caveats.append("If the cancellation conditions are met, compensation is generally the one-way basic fare plus airline fuel charge, capped by the applicable block-time amount; fuel-charge data is not present in this model.")
        elif notice < 24 and not alternative:
            # Need basic fare plus fuel surcharge for an exact result. Do not use base_fare alone.
            reasoning.append("Scenario facts indicate short-notice cancellation without an alternative; the applicable capped compensation formula may apply, but fare/fuel components are missing.")
            caveats.append("Potential cancellation compensation cannot be quantified because basic fare plus fuel charge is not provided.")
        else:
            reasoning.append("The supplied cancellation facts do not establish the short-notice/no-suitable-alternative condition for the cash formula.")
    else:
        reasoning.append("For this delayed flight, the engine reports applicable care/refund options rather than inventing a fixed cash award.")
    return PayoutResult(
        regime="DGCA CAR Section 3, Series M, Part IV",
        citation="DGCA Civil Aviation Requirements, Section 3, Series M, Part IV (Passenger Charter), effective 15 February 2023",
        applicable=True, eligible=eligible, cash_amount=amount, currency="INR",
        entitlements=entitlements, reasoning=reasoning, caveats=caveats,
    )


def _us_dot(flight: dict, delay: int, cancelled: bool, ref: FlightRef) -> PayoutResult:
    dep, arr = country_of(flight["origin"]), country_of(flight["destination"])
    domestic = dep == "US" and arr == "US"
    threshold = 180 if domestic else 360
    significant = cancelled or delay >= threshold
    passenger_declined = flight.get("passenger_declined_alternative", False)
    eligible = significant and passenger_declined
    fare = ref.base_fare
    reasoning = []
    if cancelled:
        reasoning.append("A cancelled flight can qualify for a refund if the passenger does not travel or accept alternative transportation/credit.")
    elif significant:
        reasoning.append(f"Delay meets the US DOT significant-delay threshold ({threshold} minutes) for this itinerary; refund depends on the passenger declining the changed itinerary.")
    else:
        reasoning.append(f"Delay is below the supported US DOT significant-delay threshold ({threshold} minutes).")
    if significant and not passenger_declined:
        reasoning.append("The demo scenario does not say the passenger declined alternative transportation or credit, so a refund is not established.")
    return PayoutResult(
        regime="US DOT ticket refund rules (14 CFR Part 260)",
        citation="14 CFR Part 260; US DOT Refunds guidance",
        applicable=(dep == "US" or arr == "US"), eligible=eligible,
        cash_amount=(fare if fare is not None else None) if eligible else 0.0,
        currency="USD", entitlements=["Refund to original form of payment if the passenger declines travel/alternative and the refund conditions are met"] if eligible else [],
        reasoning=reasoning,
        caveats=["US DOT refund rights are not EU-style fixed delay compensation. A fare amount and passenger choice are required to quantify the refund."],
    )


def applicable_regimes(flight: dict) -> list[str]:
    dep, arr = country_of(flight["origin"]), country_of(flight["destination"])
    carrier = CARRIERS.get(flight.get("airline_code", ""), {}).get("country")
    regimes = []
    if dep == "IN":
        regimes.append("DGCA")
    if dep in EU_EEA or (arr in EU_EEA and carrier in EU_EEA):
        regimes.append("EU261")
    if dep == "GB" or (arr == "GB" and carrier == "GB"):
        regimes.append("UK261")
    if dep == "US" or arr == "US":
        regimes.append("USDOT")
    return regimes


def compute_payout(flight: dict, ref: FlightRef, audit: Optional[AuditResult],
                   delay_minutes: Optional[int] = None, cancelled: Optional[bool] = None,
                   extraordinary: Optional[bool] = None) -> tuple[PayoutResult, list[PayoutResult]]:
    delay = int(flight.get("arrival_delay_minutes", 0)) if delay_minutes is None else int(delay_minutes)
    cancel = bool(flight.get("cancelled", False)) if cancelled is None else bool(cancelled)
    extra = (audit.extraordinary_circumstances_valid if audit else False) if extraordinary is None else bool(extraordinary)
    results: list[PayoutResult] = []
    for regime in applicable_regimes(flight):
        if regime == "DGCA":
            results.append(_dgca(flight, delay, cancel, extra))
        elif regime == "EU261":
            results.append(_eu261(flight, delay, cancel, extra))
        elif regime == "UK261":
            results.append(_uk261(flight, delay, cancel, extra))
        elif regime == "USDOT":
            results.append(_us_dot(flight, delay, cancel, ref))
    for result in results:
        _finish(result)
    if not results:
        none = PayoutResult(
            regime="No supported regime", citation="n/a", applicable=False, eligible=False,
            reasoning=["No supported passenger-rights regime matches this route and carrier."],
            caveats=["The prototype only implements India DGCA, EU261, UK261 and US DOT refund checks."],
        )
        return none, []

    # Prefer a confirmed cash-compensation result, then a refund result, then care-only.
    def rank(r: PayoutResult) -> tuple[int, float]:
        if not r.applicable:
            return (0, 0.0)
        if r.eligible and r.cash_amount is not None:
            return (3, r.cash_amount * FX_TO_INR.get(r.currency, 1.0))
        if r.eligible:
            return (2, 0.0)
        if r.entitlements:
            return (1, 0.0)
        return (0, 0.0)
    results.sort(key=rank, reverse=True)
    return results[0], results[1:]


def build_notice(flight: dict, ref: FlightRef, audit: AuditResult, primary: PayoutResult) -> str:
    who = ref.passenger_name or "the passenger"
    issue = "was cancelled" if audit.cancelled else f"arrived {audit.delay_minutes // 60}h {audit.delay_minutes % 60}m late"
    if primary.eligible and primary.cash_amount is not None and primary.cash_amount > 0:
        requested = f"the assessed amount of {primary.display_amount}"
    elif primary.entitlements:
        requested = "the applicable care, refund or re-routing entitlements; fixed cash compensation is not established by the supplied facts"
    else:
        requested = "a written eligibility decision and the legal basis for any refusal"
    lines = [
        f"Subject: Simulated passenger-rights claim assessment — {flight['flight_number']} ({ref.date or flight.get('date', 'date not supplied')})",
        "",
        f"To {airline_name(flight['airline_code'])} Customer Relations,",
        "",
        f"I, {who}, was booked on flight {flight['flight_number']} ({audit.route}), scheduled for {flight['scheduled_departure']} on {ref.date or flight.get('date', 'the date on the booking')}. The scenario records that the flight {issue}.",
        f"The airline's stated reason in this scenario was: {audit.stated_reason!r}.",
        "",
        "Scenario evidence reviewed:",
    ]
    lines.extend(f"- {item.label}: {item.detail}" for item in audit.evidence)
    lines.extend(["", f"Under the preliminary assessment for {primary.regime}, I request {requested}."])
    if primary.entitlements:
        lines.append("Potential assistance to assess: " + "; ".join(primary.entitlements) + ".")
    lines.append("Assessment reasoning:")
    lines.extend(f"- {reason}" for reason in primary.reasoning)
    if primary.caveats:
        lines.append("Facts to verify before submitting a real claim:")
        lines.extend(f"- {caveat}" for caveat in primary.caveats)
    lines.extend([
        "",
        "This letter is generated from Avyation's simulated scenario. It is not a statement that a real flight was operated or that payment is guaranteed. Please provide the applicable decision and supporting reasons in writing.",
        "",
        f"Regards,\n{who}",
    ])
    return "\n".join(lines)


async def polish_notice(draft: str) -> str:
    """Optional LLM polish; keep all legal facts, amounts and caveats unchanged."""
    out = await gemini_text(
        "Polish this simulated passenger-rights assessment letter. Preserve every fact, amount, uncertainty, caveat and legal citation. Do not turn conditional eligibility into confirmed entitlement. Add no new claims. Return only the letter text.\n\n" + draft
    )
    return out.strip() if out else draft
