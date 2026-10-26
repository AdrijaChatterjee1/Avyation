
"""Orchestrates Avyation's deterministic hackathon demo case.

All flight evidence in this workflow comes from the bundled demo dataset.
Do not present this result as a verified live flight investigation.
"""

from copy import deepcopy

from ..models import FlightRef, TicketData
from ..services import legal
from ..services.disruption import audit_flight
from ..store import get_flight


DEMO_FLIGHT_NUMBER = "6E-204"

DEMO_TICKET = TicketData(
    airline="IndiGo",
    flight_number=DEMO_FLIGHT_NUMBER,
    pnr="AVY260",
    passenger_name="DEMO PASSENGER",
    date="2026-10-20",
    origin="DEL",
    destination="BLR",
    scheduled_departure="14:30",
    ticket_class="Economy",
    base_fare=6200.0,
)


def build_demo_case() -> dict:
    """Build a complete, repeatable demo result using existing services."""

    stored_flight = get_flight(DEMO_FLIGHT_NUMBER)
    if stored_flight is None:
        raise RuntimeError(
            f"Demo flight {DEMO_FLIGHT_NUMBER} is missing from flights.json"
        )

    # Never modify the shared dataset while preparing a demo response.
    flight = deepcopy(stored_flight)

    # Keep the demo deterministic: use bundled evidence, not live weather.
    audit = audit_flight(flight)

    ticket = DEMO_TICKET
    passenger_ref = FlightRef(
        flight_number=ticket.flight_number,
        date=ticket.date,
        pnr=ticket.pnr,
        passenger_name=ticket.passenger_name,
        base_fare=ticket.base_fare,
    )

    primary, alternatives = legal.compute_payout(
        flight=flight,
        ref=passenger_ref,
        audit=audit,
    )

    # Use the template directly so the demo does not depend on an LLM call.
    notice = legal.build_notice(
        flight=flight,
        ref=passenger_ref,
        audit=audit,
        primary=primary,
    )

    return {
        "case_id": "DEMO-6E204-20261020",
        "mode": "demo",
        "is_simulated": True,
        "disclaimer": (
            "Hackathon demonstration only. Passenger details, flight disruption "
            "evidence, and the resulting assessment use fictional or bundled demo "
            "data. This is not a verified live flight investigation or legal decision."
        ),
        "ticket": ticket.model_dump(),
        "flight": {
            "flight_number": flight["flight_number"],
            "date": flight["date"],
            "origin": flight["origin"],
            "destination": flight["destination"],
            "scheduled_departure": flight["scheduled_departure"],
            "actual_departure": flight["actual_departure"],
            "arrival_delay_minutes": flight["arrival_delay_minutes"],
            "cancelled": flight["cancelled"],
            "stated_reason": flight["airline_stated_reason"],
            "data_source": "Bundled Avyation demo dataset",
        },
        "audit": audit.model_dump(),
        "payout": {
            "primary": primary.model_dump(),
            "alternatives": [
                item.model_dump() for item in alternatives
            ],
        },
        "notice_text": notice,
        "filing": {
            "available": True,
            "mode": "simulated",
            "message": (
                "The claim can be submitted to Avyation's mock demo portal. "
                "No real airline claim has been filed."
            ),
        },
    }
