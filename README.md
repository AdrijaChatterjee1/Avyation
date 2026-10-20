# ✈️ Avyation
### Know Your Rights. Understand What You May Claim.

**Avyation** is an AI-powered flight-disruption intelligence and claim-assistance platform built for **Kritical Hacks 2026**. It helps passengers investigate delays and cancellations, understand potentially applicable passenger-rights frameworks, estimate possible compensation or assistance, and prepare a claim.

The backend is built with **FastAPI**. It combines structured flight/demo data, weather information, jurisdiction-aware rules, optional AI-assisted ticket parsing, and optional TinyFish-powered live retrieval and claim filing.

> **Important:** Avyation is a hackathon prototype. Eligibility and amounts are informational estimates, not guarantees. They depend on the applicable law, route, airline, circumstances, and supporting evidence. This project does not provide legal advice.

---

## 🚨 The Problem

Flight disruption information is spread across airline policies and passenger-rights regulations. Passengers may find it difficult to determine:

- Which country's or region's rules apply to a particular flight.
- Whether a delay, cancellation, or denied boarding may qualify for compensation, a refund, or care.
- Whether an airline's stated reason for a disruption is supported by available evidence.
- What information and documents are needed to submit a claim.

## 💡 Our Solution

Avyation brings flight investigation, potential-rights assessment, and claim assistance into one workflow.

### Key capabilities

- **Ticket parsing:** Accepts a boarding pass or e-ticket image/PDF and can use Gemini vision to extract structured flight details.
- **Disruption investigation:** Compares the airline's stated reason with weather/METAR data and other flight departures where data is available.
- **Jurisdiction-aware assessment:** Evaluates potentially applicable frameworks such as DGCA, EU261, UK261, and US DOT based on the available flight information.
- **Potential payout evaluation:** Returns the primary assessment, alternative frameworks, reasoning, caveats, and a notice text.
- **Flight risk and weather watch:** Provides a flight-check summary, risk gauge, potential recovery information, agent feed, and weather-watch information.
- **Claim filing workflow:** Can submit information to a bundled demo grievance portal or use configured live filing functionality.
- **Claims list:** Shows claims held by the running application.

Availability of live integrations depends on environment configuration and third-party services. When credentials are not provided, selected features use demo data or simulated behavior.

## ⚙️ How It Works

1. **Enter or upload flight details.** Provide a flight number and, where available, travel date, PNR, passenger name, and fare.
2. **Investigate the disruption.** The backend checks available flight and weather evidence against the stated reason.
3. **Evaluate potential rights.** The rules and jurisdiction logic generate a potential payout assessment, reasoning, and caveats.
4. **Review the result.** The API returns structured evidence and guidance.
5. **Prepare or submit a claim.** The filing workflow can use the demo portal or a configured portal URL.

```text
Flight / Ticket Details
        ↓
Ticket Parsing (optional)
        ↓
Disruption Investigation
        ↓
Weather + Flight Evidence
        ↓
Jurisdiction & Payout Evaluation
        ↓
Potential Rights + Reasoning + Caveats
        ↓
Claim Filing (demo or configured live workflow)
```

## 🧠 Technology Stack

| Technology / component | Purpose |
|---|---|
| Python | Backend implementation |
| FastAPI | HTTP API and interactive API documentation |
| Uvicorn | Local ASGI server |
| Pydantic / pydantic-settings | Request/response validation and environment configuration |
| HTTPX | HTTP requests to external services |
| Gemini API (optional) | Vision-assisted extraction of ticket details |
| TinyFish (optional) | Browser-agent workflow for live retrieval and claim filing |
| Local JSON dataset | Hackathon demo flight, airport, carrier, and weather-watch data |
| Pytest | Automated tests |

The current risk score is a transparent additive baseline, not a trained machine-learning model. The local flight dataset and in-memory claims store are intended for the prototype and can later be replaced with persistent storage and real flight-data providers.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ recommended
- `pip`
- Git (if cloning the repository)
- Optional API credentials for Gemini and TinyFish if you want to enable integrations

### 1. Clone the repository

Replace the placeholder URL with your repository URL:

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
```

### 2. Create and activate a virtual environment

**Windows — Command Prompt:**

```bat
python -m venv .venv
.venv\Scripts\activate
```

**Windows — PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file from the example template:

**Windows (Command Prompt):**

```bat
copy .env.example .env
```

**PowerShell / macOS / Linux:**

```bash
cp .env.example .env
```

Open `.env` and add your credentials as needed:

```env
TINYFISH_API_KEY=your_tinyfish_api_key
GEMINI_API_KEY=your_gemini_api_key

# Optional settings; defaults are shown
TINYFISH_BASE_URL=https://agent.tinyfish.ai
GEMINI_MODEL=gemini-2.5-flash
PUBLIC_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:5173
LIVE_WEATHER=false
LIVE_FILING=true
```

Only set the credentials you have. Keep `.env` private and never commit real API keys. The settings loader ignores extra environment variables. If you do not have API keys, the backend can still run with demo/fallback behavior for supported features.

### 5. Start the backend

The run instructions use the `app.main:app` import path:

```bash
uvicorn app.main:app --reload --port 8000
```

If the server does not start, check that you are in the repository root and that the backend package is laid out as expected (including the `app` package and its `main.py`).

### 6. Open the API documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **Root URL:** http://localhost:8000/ (redirects to `/docs`)

Use Swagger UI to inspect endpoints and send test requests.

---

## 🔌 API Endpoints

| Frontend action | Endpoint | Purpose |
|---|---|---|
| Upload ticket | `POST /api/parse-ticket` | Accepts a multipart `file` (PNG, JPG, WEBP, or PDF) and returns structured ticket data; Gemini vision is used when configured. |
| Upload ticket (alias) | `POST /api/upload-ticket` | Alias for ticket parsing. |
| Investigate disruption | `POST /api/audit-disruption` | Checks the stated disruption reason against available METAR/weather and other-departure evidence. |
| Investigate (alias) | `POST /api/investigate-flight` | Alias for disruption investigation. |
| Evaluate claim | `POST /api/calculate-payout` | Evaluates potential jurisdiction, payout, entitlements, reasoning, caveats, and a notice. |
| Evaluate (alias) | `POST /api/evaluate-claim` | Alias for claim evaluation. |
| File a claim | `POST /api/execute-filing` | Runs the claim-filing workflow using the demo portal or a configured portal. |
| File claim (alias) | `POST /api/file-claim` | Alias for claim filing. |
| Check flight | `GET /api/flight-check?flight=6E-204` | Returns a combined flight-check summary. |
| Weather watch | `GET /api/weather-watch?airport=DEL` | Returns weather-watch information for an airport code. |
| My claims | `GET /api/claims` | Returns claims stored by the running application. |
| Demo portal | `GET /demo-portal` | Opens the bundled mock airline grievance form. |
| Demo submissions | `GET /demo-portal/submissions` | Shows submissions received by the mock portal. |

### Example request: evaluate a claim

Only `flight_number` is required by the documented request example. Other fields are optional and can help the assessment.

```bash
curl -X POST "http://localhost:8000/api/calculate-payout" \
  -H "Content-Type: application/json" \
  -d '{"flight_number":"AF-225","passenger_name":"Demo Passenger","pnr":"W4K9LM","date":"2026-10-20","base_fare":6200}'
```

Example request body:

```json
{
  "flight_number": "6E-204",
  "date": "2026-10-20",
  "pnr": "W4K9LM",
  "passenger_name": "Demo Passenger",
  "base_fare": 6200
}
```

Use fictional passenger details for testing. Avoid submitting real passenger information to a public or shared demo.

---

## 🧪 Demo Flights

The backend instructions identify the following sample scenarios in the bundled flight dataset. Results are illustrative and depend on the current implementation and configured data.

| Flight | Demo scenario |
|---|---|
| `6E-204` — DEL → BLR | Four-hour delay; the sample scenario questions a weather explanation using clear METAR and other-flight evidence. |
| `AF-225` — DEL → CDG | 3.5-hour delay attributed to a technical fault; used to demonstrate comparison of EU261 and DGCA outcomes. |
| `AI-805` — DEL → BOM | Thunderstorm and other disrupted flights; contrast case where the weather explanation is supported. |
| `AI-101` — DEL → LHR | Cancellation described as operational reasons. |
| `UK-955` — BOM → DEL | 2-hour-10-minute delay; sample scenario focuses on meals/care rather than cash compensation. |

These are demo cases, not verified statements about real-world flights or guaranteed legal outcomes.

---

## 🌐 Optional Live Integrations

### TinyFish claim-filing demo

The TinyFish browser agent cannot access your machine's `localhost` directly. For a live demo, expose the local backend through a secure HTTPS tunnel and configure the public URL.

1. Start the backend locally.
2. Start an HTTPS tunnel, for example:

   ```bash
   ngrok http 8000
   ```

3. Set `PUBLIC_BASE_URL` in `.env` to the HTTPS URL provided by the tunnel, then restart the backend.
4. Call `POST /api/execute-filing`. By default, the demo workflow can direct the agent to the bundled `/demo-portal` mock grievance form.
5. Check `GET /demo-portal/submissions` to inspect submissions received by the mock portal.
6. If the implementation supports it, pass `portal_url` in the filing request to target a different portal. Use only portals you are authorized to access and test.

### Live weather

Set the following in `.env` to enable the optional live weather retrieval path:

```env
LIVE_WEATHER=true
```

The audit may take longer when live retrieval is enabled. The documented behavior falls back to the bundled dataset if live weather retrieval fails.

### Integration notes

- The backend instructions describe a TinyFish request to `POST {TINYFISH_BASE_URL}/v1/automation/run` with an API key and a URL/goal payload. Check the current [TinyFish Agent API documentation](https://docs.tinyfish.ai/agent-api/reference) before relying on optional request fields or presenting the integration as production-ready.
- Live behavior depends on valid credentials, network access, third-party service availability, and the current code configuration.
- Do not use a real airline portal for automated submissions without authorization and careful review.

---

## ✅ Tests

Run the test suite from the repository root with the virtual environment activated:

```bash
python -m pytest -q
```

If tests fail, review the error output and confirm that dependencies are installed and any required environment configuration is present.

---

## 🗂️ Project Structure

The exact repository tree may vary. The backend files supplied with the project include the following responsibilities:

```text
.
├── app/
│   ├── main.py          # FastAPI app, CORS, router registration, root redirect
│   ├── config.py        # Environment-based settings
│   ├── models.py        # Pydantic request and response models
│   ├── store.py         # Demo flight data and in-memory claims store
│   ├── routers/         # API and demo-portal routes
│   ├── services/        # Assessment, risk, weather, AI and filing logic
│   └── data/
│       └── flights.json # Bundled demo flight data
├── requirements.txt
├── .env.example
└── README.md
```

This is a guide to the expected structure based on the run instructions and supplied modules; check the actual repository for files that may be named or organized differently.

---

## 🔐 Responsible AI, Privacy & Reliability

- Prefer official regulatory sources and date-relevant policy text where available.
- Show supporting evidence, reasoning, and caveats rather than presenting an unexplained result.
- Keep compensation, refunds, and care/assistance distinct.
- Make uncertainty and missing information explicit.
- Do not claim that a payout is guaranteed.
- Treat retrieved web content as evidence to evaluate, not as instructions to follow.
- Avoid storing real passenger information in demos. The current claims store is in memory and resets when the backend restarts; it is not a production database.
- Verify current regulations before relying on any compensation result. The project's DGCA cash-delay tiers are prototype rules and should be checked against current official requirements before a public release.

## 🎯 Target Users

- Passengers affected by delays, cancellations, or denied boarding.
- Frequent and business travellers who want a quick rights check.
- International travellers navigating multiple jurisdictions.
- Travel agencies and travel platforms that may integrate passenger-rights assessment into their services.

## 💰 Proposed Revenue Model

Avyation proposes a business-to-business-first model:

1. **B2B SaaS subscriptions** for travel agencies, online travel agencies, and travel platforms.
2. **API usage fees** for partners processing flight-disruption checks.
3. **Premium passenger assistance** for guided claim preparation and documentation support.
4. **White-label integrations** that let travel partners offer the service under their own branding.

These are proposed business models, not existing commercial revenue.

## 🛣️ Roadmap

- [ ] Expand airline and jurisdiction coverage.
- [ ] Validate and version regulatory rules against official sources.
- [ ] Improve source validation and conflicting-evidence handling.
- [ ] Replace demo flight data with a reliable live provider.
- [ ] Add persistent, secure claim storage and user authentication.
- [ ] Improve edge-case handling, explanations, and multilingual guidance.
- [ ] Develop partner-facing APIs and white-label integrations.
- [ ] Explore guided claim-document preparation and progress tracking.
- [ ] Evaluate and train a dedicated risk-prediction model using appropriate data.

## 🤝 Contributing

Contributions, suggestions, and feedback are welcome. When contributing:

- Document changes to assessment rules and data sources.
- Validate legal and policy logic against reliable, current sources.
- Add or update tests for changed behavior.
- Never commit `.env` files, API keys, or sensitive passenger information.
- Clearly distinguish implemented functionality from proposed features.

## 👥 Team

**Project:** Avyation  
**Event:** Kritical Hacks 2026  
**Team members:** Angel Dhiman · Aashna Sharma · Adrija Chatterjee · Janvi Upreti

---

*Know your rights. Make informed travel decisions.*
