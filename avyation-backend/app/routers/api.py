from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ..config import settings
from ..models import (AuditResult, Claim, FilingRequest, FilingResult, FlightRef,
                      PayoutResponse, RiskResult)
from ..services import filer, legal
from ..services.disruption import audit_flight, fetch_live_weather
from ..services.risk import score_flight
from ..services.ticket_parser import parse_ticket as run_parse_ticket
from ..services.tinyfish import tinyfish
from ..store import AIRPORTS, WEATHER_WATCH, get_flight, list_claims

router = APIRouter(prefix="/api")

ALLOWED_UPLOADS = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _flight_or_404(flight_number: str) -> dict:
    flight = get_flight(flight_number)
    if not flight:
        raise HTTPException(404, f"Flight '{flight_number}' is not in the demo dataset. "
                                 "Try 6E-204, AF-225, AI-101, UK-955 or AI-805.")
    return flight


async def _audit(flight: dict) -> AuditResult:
    icao = AIRPORTS.get(flight["origin"], {}).get("icao")
    live = await fetch_live_weather(icao) if icao else None
    return audit_flight(flight, live)


def _issue_label(audit: AuditResult) -> str:
    if audit.cancelled:
        return "Cancelled"
    return f"{audit.delay_minutes // 60}h delay" if audit.delay_minutes >= 60 else f"{audit.delay_minutes} min delay"


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "tinyfish_configured": tinyfish.enabled,
        "llm_configured": bool(settings.gemini_api_key),
        "live_weather": tinyfish.enabled and settings.live_weather,
        "live_filing": tinyfish.enabled and settings.live_filing,
    }


# ------------------------------------------------------------ 1. ticket parsing
@router.post("/parse-ticket")
@router.post("/upload-ticket")  # alias used in the architecture diagram
async def parse_ticket(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_UPLOADS:
        raise HTTPException(415, f"Unsupported file type '{file.content_type}'. Upload PNG, JPG, WEBP or PDF.")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 10 MB).")
    ticket, source = await run_parse_ticket(data, file.content_type)
    return {"ticket": ticket, "source": source}


# ------------------------------------------------------------ 2. disruption audit
@router.post("/audit-disruption", response_model=AuditResult)
@router.post("/investigate-flight", response_model=AuditResult)  # alias
async def audit_disruption(ref: FlightRef):
    return await _audit(_flight_or_404(ref.flight_number))


# ------------------------------------------------------------ 3. payout + notice
@router.post("/calculate-payout", response_model=PayoutResponse)
@router.post("/evaluate-claim", response_model=PayoutResponse)  # alias
async def calculate_payout(ref: FlightRef):
    flight = _flight_or_404(ref.flight_number)
    audit = await _audit(flight)
    primary, alternatives = legal.compute_payout(flight, ref, audit)
    notice = await legal.polish_notice(legal.build_notice(flight, ref, audit, primary))
    return PayoutResponse(flight_number=flight["flight_number"], primary=primary,
                          alternatives=alternatives, audit=audit, notice_text=notice)


# ------------------------------------------------------------ 4. filing (TinyFish agent)
@router.post("/execute-filing", response_model=FilingResult)
@router.post("/file-claim", response_model=FilingResult)  # alias
async def execute_filing(req: FilingRequest):
    flight = _flight_or_404(req.flight_number)
    audit = await _audit(flight)
    primary, _ = legal.compute_payout(flight, req, audit)
    if not primary.eligible and not primary.entitlements:
        raise HTTPException(409, "Nothing to claim for this flight: " + " ".join(primary.reasoning))

    notice = req.notice_text or await legal.polish_notice(legal.build_notice(flight, req, audit, primary))
    portal_url = req.portal_url or f"{settings.public_base_url.rstrip('/')}/demo-portal"
    if not portal_url.startswith(("http://", "https://")):
        raise HTTPException(422, "portal_url must be an http(s) URL")

    return await filer.file_claim(
        flight=flight, route=audit.route, issue=_issue_label(audit),
        amount=(primary.display_amount if primary.eligible and primary.display_amount else "Meals"),
        pnr=req.pnr, name=req.passenger_name, email=req.email, notice=notice, portal_url=portal_url,
    )


# ------------------------------------------------------------ dashboard helpers
@router.get("/flight-check")
async def flight_check(flight: str = Query(..., examples=["6E-204"]),
                       date: Optional[str] = None, pnr: Optional[str] = None):
    """One call that powers the whole dashboard: risk gauge, potential recovery,
    agent live feed and weather watch."""
    rec = _flight_or_404(flight)
    ref = FlightRef(flight_number=rec["flight_number"], date=date or rec["date"], pnr=pnr)
    risk: RiskResult = score_flight(rec)
    audit = await _audit(rec)
    actual, _ = legal.compute_payout(rec, ref, audit)
    hypo, _ = legal.compute_payout(rec, ref, None, delay_minutes=180, cancelled=False, extraordinary=False)
    short = hypo.regime.split()[0]

    feed = [
        {"text": "Reading boarding pass with Vision AI", "state": "done"},
        {"text": "Fetching METAR and departure logs via TinyFish", "state": "done"},
        {"text": audit.verdict, "state": "done" if audit.airline_at_fault else "warn"},
        {"text": f"Jurisdiction matched: {actual.regime}", "state": "done"},
        {"text": f"Entitlement calculated: {actual.display_amount or 'care entitlements only'}", "state": "done"},
        {"text": "TinyFish Web Agent filing on airline portal", "state": "pending"},
    ]
    return {
        "flight": rec["flight_number"], "date": ref.date,
        "route": {"origin": rec["origin"], "destination": rec["destination"],
                  "scheduled_departure": rec["scheduled_departure"]},
        "risk": risk,
        "potential_recovery": {
            "amount": hypo.cash_amount, "currency": hypo.currency,
            "display_amount": hypo.display_amount, "regime": hypo.regime,
            "note": f"Estimated cash owed on {rec['flight_number']} if delayed 3h+ ({short}).",
        },
        "agent_feed": feed,
        "weather_watch": WEATHER_WATCH.get(rec["origin"]),
    }


@router.get("/weather-watch")
async def weather_watch(airport: str = Query("DEL", min_length=3, max_length=3)):
    watch = WEATHER_WATCH.get(airport.upper())
    if not watch:
        raise HTTPException(404, f"No weather watch configured for {airport.upper()}")
    return watch


@router.get("/claims", response_model=list[Claim])
async def claims():
    return list_claims()
