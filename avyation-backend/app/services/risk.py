"""Pre-emptive Delay Risk Score.

This is a transparent additive baseline, so judges can see exactly why a flight scores what it
does. Swap `score_flight` for a trained classifier (features: inbound delay, forecast
visibility, route on-time history, hub congestion) without touching the API contract.

Reference calibration: 6E-204 -> 28 base + 28 (inbound late) + 22 (low-vis forecast) - 6 (good
route history) = 72, matching the dashboard card.
"""
from ..models import RiskFactor, RiskResult

BASE = 28


def _visibility_points(vis_m: int) -> int:
    if vis_m <= 400:
        return 22
    if vis_m <= 1000:
        return 14
    if vis_m <= 3000:
        return 6
    return 0


def score_flight(flight: dict) -> RiskResult:
    inbound_pts = min(35, int(flight.get("inbound_aircraft_delay_minutes", 0) * 0.3))
    vis_pts = _visibility_points(int(flight.get("forecast_visibility_m", 9999)))
    history_pts = -round((flight.get("route_on_time_rate", 0.7) - 0.70) * 75)

    total = max(3, min(97, BASE + inbound_pts + vis_pts + history_pts))
    if total >= 60:
        label = "High chance of 2h+ delay"
    elif total >= 35:
        label = "Moderate chance of delay"
    else:
        label = "Low chance of delay"

    factors = [
        RiskFactor(label="Inbound aircraft running late", points=inbound_pts),
        RiskFactor(label="Low visibility forecast", points=vis_pts),
        RiskFactor(label="Route on-time history", points=history_pts),
    ]
    return RiskResult(
        flight_number=flight["flight_number"], origin=flight["origin"],
        destination=flight["destination"], scheduled_departure=flight["scheduled_departure"],
        score=total, label=label, factors=factors,
    )
