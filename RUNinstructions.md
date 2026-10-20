# Avyation backend (FastAPI)

Predictive flight intelligence + autonomous claim recovery. Built for Kritical Hacks 2026.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # add TINYFISH_API_KEY / GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs. Tests: `python -m pytest -q`.

With **no keys** everything still works: the ticket parser returns a demo ticket, METAR comes
from the bundled dataset, and filing runs in `simulated` mode. Add keys to go live.

## Endpoints

| Frontend action | Endpoint (aliases from your architecture diagram) | What it does |
|---|---|---|
| Upload Ticket | `POST /api/parse-ticket` (`/api/upload-ticket`) | multipart `file` (png/jpg/webp/pdf) -> Gemini vision -> structured ticket JSON |
| Investigate | `POST /api/audit-disruption` (`/api/investigate-flight`) | checks the airline's stated reason against METAR + other departures |
| Evaluate | `POST /api/calculate-payout` (`/api/evaluate-claim`) | jurisdiction match (DGCA / EU261 / UK261 / US DOT), payout, legal notice |
| File a Claim | `POST /api/execute-filing` (`/api/file-claim`) | TinyFish web agent fills the airline grievance form |
| Dashboard / "Check my flight" | `GET /api/flight-check?flight=6E-204` | risk gauge, potential recovery, agent feed, weather watch in one call |
| Weather watch | `GET /api/weather-watch?airport=DEL` | |
| My Claims | `GET /api/claims` | |

Body for the POST steps: `{"flight_number": "6E-204", "date": "2026-10-20", "pnr": "W4K9LM", "passenger_name": "Angie", "base_fare": 6200}` (only `flight_number` is required).

```bash
curl -X POST localhost:8000/api/calculate-payout -H 'content-type: application/json' \
  -d '{"flight_number":"AF-225","passenger_name":"Angie","pnr":"W4K9LM"}'
```

## Demo flights (`app/data/flights.json`)

| Flight | Story |
|---|---|
| `6E-204` DEL->BLR | 4h delay, "weather" excuse disproved (clear METAR, 14/16 others on time). DGCA, ₹10,000. Risk score 72, matching your dashboard. |
| `AF-225` DEL->CDG | 3.5h delay, technical fault. EU261 (€300 after the 50% reduction) beats DGCA. |
| `AI-805` DEL->BOM | Real thunderstorm, other flights disrupted: excuse is valid, no cash. Good contrast case. |
| `AI-101` DEL->LHR | Cancelled, "operational reasons". |
| `UK-955` BOM->DEL | 2h10m delay: meals only. |

## TinyFish in the live demo

1. `ngrok http 8000`, then set `PUBLIC_BASE_URL` to the https URL (TinyFish drives a cloud browser, so it can't reach `localhost`).
2. `POST /api/execute-filing` now sends the agent to `PUBLIC_BASE_URL/demo-portal`, a mock airline grievance form. It fills the PNR, name and category, pastes the notice and returns the tracking reference. `GET /demo-portal/submissions` proves it landed.
3. Pass `portal_url` in the request to point it at a real airline portal instead.
4. Set `LIVE_WEATHER=true` to have TinyFish read live METAR from aviationweather.gov during the audit (slower; falls back to the dataset on failure).

## Things to verify before you present

- **TinyFish request shape.** The client uses `POST {base}/v1/automation/run` with `X-API-Key` and `{"url", "goal"}`, per the TinyFish docs. Check https://docs.tinyfish.ai/agent-api/reference for any optional fields you want. The Search/Fetch APIs from your pitch aren't wired separately; the agent does the METAR extraction.
- **DGCA rules.** Cash tiers (₹5,000 / 7,500 / 10,000 by block time, from 3h delay) follow your product spec and dashboard. The official CAR pays cash mainly for cancellations and denied boarding. Read the current text and tweak `DGCA_CASH_DELAY_MIN` in `services/legal.py` so a judge can't catch you on it.
- **Risk score** is a transparent additive baseline in `services/risk.py`, not a trained model. Pitch it as the baseline and name what you'd train next.
- **Not legal advice**, and claims are stored in memory (they reset on restart).
