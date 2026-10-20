from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TicketData(BaseModel):
    """Structured fields extracted from a boarding pass / e-ticket."""

    airline: Optional[str] = None
    flight_number: str
    pnr: Optional[str] = None
    passenger_name: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    origin: Optional[str] = None  # IATA
    destination: Optional[str] = None  # IATA
    scheduled_departure: Optional[str] = None  # HH:MM local
    ticket_class: Optional[str] = None
    base_fare: Optional[float] = None


class FlightRef(BaseModel):
    """Minimal identifier the frontend sends for every step after parsing."""

    flight_number: str = Field(examples=["6E-204"])
    date: Optional[str] = None
    pnr: Optional[str] = None
    passenger_name: Optional[str] = None
    base_fare: Optional[float] = None


class EvidenceItem(BaseModel):
    label: str
    detail: str
    supports_claim: Optional[bool] = None


class AuditResult(BaseModel):
    flight_number: str
    route: str
    stated_reason: str
    reason_category: str
    delay_minutes: int
    cancelled: bool
    extraordinary_circumstances_valid: bool
    airline_at_fault: bool
    verdict: str
    evidence: list[EvidenceItem]
    data_source: str


class RiskFactor(BaseModel):
    label: str
    points: int


class RiskResult(BaseModel):
    flight_number: str
    origin: str
    destination: str
    scheduled_departure: str
    score: int
    label: str
    factors: list[RiskFactor]


class PayoutResult(BaseModel):
    regime: str
    citation: str
    applicable: bool
    eligible: bool
    cash_amount: Optional[float] = None
    currency: str = "INR"
    display_amount: str = ""
    entitlements: list[str] = []
    reasoning: list[str] = []
    caveats: list[str] = []


class PayoutResponse(BaseModel):
    flight_number: str
    primary: PayoutResult
    alternatives: list[PayoutResult]
    audit: AuditResult
    notice_text: str


class FilingRequest(FlightRef):
    notice_text: Optional[str] = None
    portal_url: Optional[str] = None  # defaults to the bundled demo portal
    email: Optional[str] = None


class FilingResult(BaseModel):
    claim_id: str
    mode: Literal["live", "simulated"]
    status: str
    tracking_reference: Optional[str] = None
    portal_url: str
    steps: list[str]
    raw_result: Optional[Any] = None
    error: Optional[str] = None


class Claim(BaseModel):
    id: str
    flight: str
    route: str
    issue: str
    amount: str
    status: str
    tracking_reference: Optional[str] = None
