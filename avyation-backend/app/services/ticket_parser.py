"""POST /api/parse-ticket: boarding pass image/PDF -> structured JSON via a multimodal LLM."""
import re
from typing import Tuple

from ..models import TicketData
from ..store import pretty_flight_no
from .llm import gemini_json

PROMPT = """You are reading an airline boarding pass or e-ticket. Extract these fields and
return ONLY a JSON object with exactly these keys (use null when a field is not visible):
airline, flight_number (e.g. "6E 204"), pnr (6 characters), passenger_name,
date (YYYY-MM-DD), origin (3-letter IATA), destination (3-letter IATA),
scheduled_departure (HH:MM, 24h, local), ticket_class, base_fare (number only, no currency).
Do not guess values that are not printed on the document."""

# Used when no LLM key is configured or the model call fails, so the demo never dead-ends.
DEMO_TICKET = TicketData(
    airline="IndiGo", flight_number="6E-204", pnr="W4K9LM", passenger_name="ANGIE DHIMAN",
    date="2026-10-20", origin="DEL", destination="BLR", scheduled_departure="14:30",
    ticket_class="Economy", base_fare=6200.0,
)


async def parse_ticket(data: bytes, mime_type: str) -> Tuple[TicketData, str]:
    raw = await gemini_json(PROMPT, file_bytes=data, mime_type=mime_type)
    if not raw or not raw.get("flight_number"):
        return DEMO_TICKET, "demo-fallback"
    raw["flight_number"] = pretty_flight_no(str(raw["flight_number"]))
    for key in ("origin", "destination"):
        if raw.get(key):
            raw[key] = str(raw[key]).strip().upper()[:3]
    if raw.get("pnr"):
        raw["pnr"] = re.sub(r"[^A-Z0-9]", "", str(raw["pnr"]).upper())
    if raw.get("base_fare") is not None:
        try:
            raw["base_fare"] = float(raw["base_fare"])
        except (TypeError, ValueError):
            raw["base_fare"] = None
    allowed = TicketData.model_fields.keys()
    return TicketData(**{k: v for k, v in raw.items() if k in allowed}), "gemini"
