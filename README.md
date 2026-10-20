# ✈️ Avyation
### Know Your Rights. Understand What You May Claim.

**Avyation** is an AI-powered flight compensation intelligence platform designed to help passengers understand their potential rights when flights are delayed, cancelled, or affected by denied boarding.

By combining live airline-policy retrieval, country-specific passenger-rights regulations, and structured eligibility assessment, Avyation aims to turn confusing travel rules into clear, source-backed guidance.

> **Built for Kritical Hacks 2026** — making flight disruption rights easier to understand and navigate.

---

## 🚨 The Problem

Flight disruptions can leave passengers confused about their rights and the next steps they should take.

- **Fragmented information:** Airline policies and passenger-rights regulations are spread across different sources.
- **Jurisdictional complexity:** Applicable rights depend on factors such as the route, operating carrier, disruption type, and governing regulations.
- **Unclear eligibility:** Passengers may struggle to determine whether compensation, a refund, or assistance may apply.
- **Difficult claim processes:** Finding relevant rules and understanding the required documentation can be time-consuming.

## 💡 Our Solution

Avyation aims to simplify flight-disruption rights assessment through an integrated workflow that connects current information with structured decision-making.

### Key Features

- **Live policy retrieval:** Uses TinyFish to retrieve relevant information from airline policies and regulatory sources.
- **AI-powered information extraction:** Identifies relevant clauses, conditions, and requirements from retrieved content.
- **Jurisdiction-aware assessment:** Determines which passenger-rights framework may apply based on flight and disruption details.
- **Structured eligibility evaluation:** Applies explicit rules to assess potential eligibility and applicable compensation where supported by the relevant framework.
- **Source-backed explanations:** Connects assessments to supporting policy or regulatory information.
- **Claim guidance:** Helps passengers understand potential next steps and documentation requirements.

*Compensation eligibility and amounts depend on the applicable rules and individual circumstances. Avyation provides guidance, not a guarantee of payment or a substitute for legal advice.*

---

## ⚙️ How It Works

1. **Enter flight details** — Provide the route, airline, flight information, and disruption details.
2. **Retrieve relevant sources** — TinyFish retrieves relevant airline policies and official regulatory information.
3. **Extract and analyze** — AI identifies relevant clauses, conditions, and jurisdictional factors.
4. **Evaluate potential rights** — A structured rules engine evaluates eligibility and applicable outcomes against the available evidence.
5. **Present the result** — The passenger receives an explanation of potential rights, supporting sources, and recommended next steps.

```text
Flight & Disruption Details
          ↓
TinyFish Live Retrieval
          ↓
Policy & Regulation Extraction
          ↓
Jurisdiction Resolution
          ↓
Rules-Based Assessment
          ↓
Potential Rights + Evidence + Claim Guidance
```

---

## 🧠 Technology & Architecture

| Component | Purpose |
|---|---|
| TinyFish | Live web retrieval of relevant airline policies and regulatory information |
| AI / LLM | Extracting and interpreting relevant policy clauses |
| Jurisdiction resolver | Identifying the potentially applicable passenger-rights framework |
| Rules engine | Applying explicit eligibility conditions and supported calculations |
| Source-backed output | Explaining assessments with relevant evidence |

The architecture separates AI-assisted document interpretation from structured eligibility evaluation to improve traceability and reduce unsupported conclusions.

*The table describes the intended architecture; retain only components that are actually integrated in the submitted implementation.*

---

## 🎯 Target Users

- **Disrupted passengers** — Travellers facing delays, cancellations, or denied boarding.
- **Frequent and business travellers** — Passengers who need quick, reliable rights checks.
- **International travellers** — People navigating different countries' regulations and airline policies.
- **Travel platforms and agencies** — Potential business customers seeking to integrate rights-assessment capabilities.

---

## 💰 Revenue Model

Avyation proposes a business-to-business-first revenue model:

1. **B2B SaaS subscriptions:** Subscription plans for travel agencies, online travel agencies, and travel platforms.
2. **API usage fees:** Usage-based pricing for partners processing flight-disruption checks.
3. **Premium passenger services:** Potential future paid assistance with claim preparation, documentation, and next steps.

A white-label offering could allow travel platforms to provide Avyation-powered assessments under their own branding.

These are proposed revenue streams, not claims of existing commercial revenue.

---

## 🌍 Impact & Future Scope

Avyation aims to make passenger-rights information more accessible, understandable, and actionable.

Potential future improvements include:

- Expanding coverage across additional countries and airlines.
- Maintaining version-aware regulatory information with effective dates.
- Improving source validation and handling conflicting policies.
- Supporting multilingual passenger guidance.
- Adding claim-document preparation and progress tracking.
- Integrating with travel booking platforms through APIs and white-label deployments.

---

## 🔐 Responsible AI & Reliability

Passenger-rights assessments require careful handling of legal and policy information.

Avyation's design principles include:

- Prioritizing official regulatory sources where available.
- Linking conclusions to supporting evidence.
- Distinguishing compensation, refunds, and care or assistance.
- Accounting for jurisdictional conditions and exceptions.
- Avoiding guaranteed payout claims.
- Making uncertainty and missing information explicit.
- Treating retrieved content as evidence to analyze, not as instructions to follow.

Regulations and airline policies can change. Assessments should use applicable, date-relevant sources and communicate uncertainty when evidence is incomplete.

---

## 🚀 Getting Started

Setup instructions depend on the current repository and its implemented stack.

### Prerequisites

- Git
- The language runtime and dependencies used by the project
- A TinyFish API key if live retrieval is enabled
- Any additional model-provider credentials required by the implementation

### Installation

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
```

Install the dependencies using the package manager and manifest included in the repository.

### Environment Configuration

Create a local `.env` file if the application uses environment variables. For example:

```env
TINYFISH_API_KEY=your_tinyfish_api_key
```

Add only the additional environment variables required by your implementation. Keep API keys private and ensure `.env` is excluded from version control.

### Run the Application

Use the actual startup command documented by your project, such as the command configured for its backend or frontend.

*Replace these setup placeholders with the verified installation, configuration, and run commands before publishing the README.*

---

## 🛣️ Roadmap

- [ ] Expand airline and jurisdiction coverage.
- [ ] Strengthen regulatory versioning and source validation.
- [ ] Improve assessment explanations and edge-case handling.
- [ ] Develop partner-facing API and white-label integrations.
- [ ] Explore guided claim preparation and document support.

---

## 🤝 Contributing

Contributions, suggestions, and feedback are welcome. If you contribute, please document changes, validate relevant rules against reliable sources, and avoid committing secrets or sensitive passenger information.

## ⚖️ Disclaimer

Avyation is an informational project intended to help passengers understand potentially applicable flight-disruption rights. It does not guarantee compensation, replace official determinations, or provide legal advice. Final outcomes depend on the applicable law, flight circumstances, evidence, and decisions by the relevant airline or authority.

## 👥 Team

**Project:** Avyation  
**Event:** Kritical Hacks 2026
**Team Members:** 
Angel Dhiman
Aashna Sharma
Adrija Chatterjee
Janvi Upretu

---

*Know your rights. Make informed travel decisions.*
