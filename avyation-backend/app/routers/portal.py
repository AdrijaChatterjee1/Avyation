"""A realistic mock airline grievance portal the TinyFish agent can drive during the live demo.

It must be reachable from the internet (TinyFish runs a cloud browser): expose the backend with
ngrok/cloudflared and set PUBLIC_BASE_URL to that URL.
"""
import html

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from ..store import new_reference

router = APIRouter()
SUBMISSIONS: list[dict] = []

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SkyWays Air - Passenger Grievance</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:560px;margin:40px auto;padding:0 16px;color:#1b2540}}
label{{display:block;margin-top:14px;font-weight:600}}
input,select,textarea{{width:100%;padding:10px;margin-top:6px;border:1px solid #b9c2d6;border-radius:8px;font:inherit;box-sizing:border-box}}
button{{margin-top:20px;padding:12px 20px;border:0;border-radius:8px;background:#5b3df5;color:#fff;font-weight:600;cursor:pointer}}
.ref{{font-size:1.4rem;font-weight:700;background:#eef;padding:12px;border-radius:8px}}
</style></head><body>{body}</body></html>"""

FORM = """<h1>SkyWays Air</h1><h2>Passenger Grievance Form</h2>
<p>Demo portal for Avyation. Not a real airline.</p>
<form method="post" action="/demo-portal/submit">
<label for="pnr">PNR / Booking reference</label><input id="pnr" name="pnr" required>
<label for="name">Passenger name</label><input id="name" name="name" required>
<label for="email">Email (optional)</label><input id="email" name="email" type="email">
<label for="category">Category</label>
<select id="category" name="category">
<option>Baggage</option><option>Refund</option><option>Staff behaviour</option>
<option>Delay / Cancellation Compensation</option><option>Other</option></select>
<label for="description">Description</label><textarea id="description" name="description" rows="10" required></textarea>
<button type="submit">Submit grievance</button></form>"""


@router.get("/demo-portal", response_class=HTMLResponse)
async def portal_form():
    return PAGE.format(body=FORM)


@router.post("/demo-portal/submit", response_class=HTMLResponse)
async def portal_submit(pnr: str = Form(...), name: str = Form(...), category: str = Form("Other"),
                        description: str = Form(...), email: str = Form("")):
    ref = new_reference("SKY")
    SUBMISSIONS.append({"ref": ref, "pnr": pnr, "name": name, "category": category,
                        "description": description, "email": email})
    body = (f"<h1>Grievance received</h1><p>Thank you, {html.escape(name)}. Your complaint has been registered.</p>"
            f"<p>Tracking reference:</p><div class='ref' id='tracking-reference'>{ref}</div>"
            f"<p>Category: {html.escape(category)}</p>")
    return PAGE.format(body=body)


@router.get("/demo-portal/submissions")
async def portal_submissions():
    """Handy for showing judges that the agent really filed the form."""
    return SUBMISSIONS
