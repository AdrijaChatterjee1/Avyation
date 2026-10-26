from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_dashboard_matches_frontend_mock():
    d = client.get("/api/flight-check", params={"flight": "6E-204"}).json()
    assert d["risk"]["score"] == 72
    assert [f["points"] for f in d["risk"]["factors"]] == [28, 22, -6]
    assert d["potential_recovery"]["display_amount"] == "₹10,000"
    assert d["weather_watch"]["headline"] == "Dense fog"


def test_weather_excuse_disproved():
    a = client.post("/api/audit-disruption", json={"flight_number": "6E 204"}).json()
    assert a["reason_category"] == "weather"
    assert a["airline_at_fault"] is True
    assert "disproved" in a["verdict"]


def test_valid_weather_excuse_not_at_fault():
    a = client.post("/api/audit-disruption", json={"flight_number": "AI-805"}).json()
    assert a["extraordinary_circumstances_valid"] is True
    assert a["airline_at_fault"] is False


def test_domestic_dgca_payout_and_notice():
    p = client.post("/api/calculate-payout", json={"flight_number": "6E-204", "passenger_name": "Angie", "pnr": "W4K9LM"}).json()
    assert p["primary"]["display_amount"] == "₹10,000"
    assert "DGCA" in p["primary"]["regime"]
    assert "W4K9LM" in p["notice_text"]


def test_eu261_beats_dgca_for_air_france():
    p = client.post("/api/calculate-payout", json={"flight_number": "AF-225"}).json()
    assert p["primary"]["regime"].startswith("EU261")
    assert p["primary"]["cash_amount"] == 300  # 3h30 delay on 3,500 km+ -> 50% of EUR 600
    assert any("DGCA" in a["regime"] for a in p["alternatives"])


def test_short_delay_only_meals():
    p = client.post("/api/calculate-payout", json={"flight_number": "UK-955"}).json()
    assert p["primary"]["eligible"] is False
    assert "Meals and refreshments" in p["primary"]["entitlements"]


def test_unknown_flight_404():
    assert client.post("/api/audit-disruption", json={"flight_number": "XX-999"}).status_code == 404


def test_simulated_filing_and_claims_list():
    r = client.post("/api/execute-filing", json={"flight_number": "6E-204", "pnr": "W4K9LM", "passenger_name": "Angie"}).json()
    assert r["mode"] in ("simulated", "live")
    assert r["tracking_reference"]
    assert client.get("/api/claims").json()[0]["flight"] == "6E-204"


def test_demo_portal_roundtrip():
    assert "Passenger Grievance Form" in client.get("/demo-portal").text
    out = client.post("/demo-portal/submit", data={"pnr": "W4K9LM", "name": "Angie", "category": "Delay / Cancellation Compensation", "description": "test"})
    assert "tracking-reference" in out.text


def test_ticket_upload_falls_back_without_llm():
    r = client.post("/api/upload-ticket", files={"file": ("bp.png", b"\x89PNG fake", "image/png")}).json()
    assert r["ticket"]["flight_number"]
    assert client.post("/api/parse-ticket", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 415


def test_demo_case_is_complete_and_explicitly_simulated():
    response = client.get("/api/demo-case")

    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "demo"
    assert data["is_simulated"] is True
    assert data["ticket"]["passenger_name"] == "DEMO PASSENGER"
    assert data["ticket"]["pnr"] == "AVY260"

    assert data["flight"]["flight_number"] == "6E-204"
    assert data["flight"]["arrival_delay_minutes"] == 240

    assert data["audit"]["data_source"] == "Avyation demo dataset"
    assert "primary" in data["payout"]
    assert data["notice_text"]
    assert data["filing"]["mode"] == "simulated"
    assert "fictional" in data["disclaimer"].lower()

