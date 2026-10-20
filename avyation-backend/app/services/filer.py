"""POST /api/execute-filing: the TinyFish highlight.

A TinyFish web agent opens the airline grievance form and fills it in from a natural-language goal.
With no TINYFISH_API_KEY (or LIVE_FILING=false) we run in 'simulated' mode so the UI flow still works.
"""
import json
from typing import Any, Optional

from ..config import settings
from ..models import FilingResult
from ..store import add_claim, new_reference
from .tinyfish import TinyFishError, tinyfish


def build_goal(pnr: Optional[str], name: Optional[str], notice: str, email: Optional[str]) -> str:
    return f"""You are filing a flight compensation complaint on this airline grievance page.
1. Find the grievance / feedback / complaint form on this page (follow the link if needed).
2. Enter PNR '{pnr or ''}' and passenger name '{name or ''}'.{f" Use email '{email}'." if email else ""}
3. Select category 'Delay / Cancellation Compensation' (or the closest option).
4. Paste the following legal notice into the description / message box exactly as written:
---
{notice}
---
5. Submit the form. Do not change any other settings and never enter payment details.
6. When the confirmation page appears, return JSON: {{"tracking_reference": "<reference shown>", "confirmation_text": "<short confirmation message>"}}."""


def _extract_reference(result: Any) -> Optional[str]:
    if isinstance(result, dict):
        for key, val in result.items():
            if "track" in key.lower() or "reference" in key.lower():
                return str(val)
        return json.dumps(result)[:120]
    return str(result)[:120] if result else None


async def file_claim(*, flight: dict, route: str, issue: str, amount: str, pnr: Optional[str],
                     name: Optional[str], email: Optional[str], notice: str,
                     portal_url: str) -> FilingResult:
    steps = ["Legal notice drafted", f"Opening airline portal: {portal_url}"]
    live = tinyfish.enabled and settings.live_filing
    reference: Optional[str] = None
    raw: Any = None
    error: Optional[str] = None
    status = "Filed"

    if live:
        try:
            raw = await tinyfish.run(portal_url, build_goal(pnr, name, notice, email), timeout=300)
            reference = _extract_reference(raw)
            steps += ["TinyFish web agent filled and submitted the form", f"Confirmation captured: {reference}"]
        except TinyFishError as exc:
            error = str(exc)
            status = "Filing failed"
            steps.append(f"TinyFish run failed: {exc}")
    else:
        reference = new_reference("AVY-SIM")
        raw = {"simulated": True}
        steps += ["SIMULATED: no TinyFish key configured; skipped real browser automation",
                  f"Simulated tracking reference: {reference}"]

    claim = add_claim(flight["flight_number"], route, issue, amount, status, reference)
    return FilingResult(
        claim_id=claim.id, mode="live" if live else "simulated", status=status,
        tracking_reference=reference, portal_url=portal_url, steps=steps, raw_result=raw, error=error,
    )
