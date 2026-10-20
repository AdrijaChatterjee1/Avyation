"""Demo flight database + in-memory claim store.

For the hackathon the 'flight delay DB' is a local JSON file so we don't pay for
FlightAware/Cirium. Swap `get_flight` for a real provider later; nothing else changes.
"""
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Claim

_DATA = json.loads((Path(__file__).parent / "data" / "flights.json").read_text(encoding="utf-8"))

AIRPORTS: dict = _DATA["airports"]
CARRIERS: dict = _DATA["carriers"]
WEATHER_WATCH: dict = _DATA["weather_watch"]
FLIGHTS: dict = _DATA["flights"]


def normalize_flight_no(raw: str) -> str:
    """'6E-204', '6e 204', '6E204' -> '6E204'."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def pretty_flight_no(raw: str) -> str:
    n = normalize_flight_no(raw)
    m = re.match(r"^([A-Z0-9]{2})(\d{1,4})$", n)
    return f"{m.group(1)}-{m.group(2)}" if m else raw.upper()


def get_flight(flight_number: str) -> Optional[dict]:
    return FLIGHTS.get(normalize_flight_no(flight_number))


def airline_name(code: str) -> str:
    return CARRIERS.get(code, {}).get("name", code)


# ---------------------------------------------------------------- claims
_CLAIMS: list[Claim] = [
    Claim(id="CLM-1003", flight="6E-204", route="DEL → BLR", issue="4h delay",
          amount="₹10,000", status="Filed"),
    Claim(id="CLM-1002", flight="AI-101", route="DEL → LHR", issue="Cancelled",
          amount="€600", status="Paid"),
    Claim(id="CLM-1001", flight="UK-955", route="BOM → DEL", issue="2h delay",
          amount="Meals", status="Rejected, appealing"),
]


def list_claims() -> list[Claim]:
    return list(_CLAIMS)


def add_claim(flight: str, route: str, issue: str, amount: str, status: str,
              tracking_reference: Optional[str] = None) -> Claim:
    claim = Claim(
        id=f"CLM-{1000 + len(_CLAIMS) + 1}",
        flight=flight, route=route, issue=issue, amount=amount, status=status,
        tracking_reference=tracking_reference,
    )
    _CLAIMS.insert(0, claim)
    return claim


def new_reference(prefix: str = "AVY") -> str:
    stamp = datetime.now(timezone.utc).strftime("%y%m%d")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6].upper()}"
