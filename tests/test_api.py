from fastapi.testclient import TestClient

from app.main import SECURITY_HEADERS, app

client = TestClient(app)
GOOD = {"amount": "125.50", "currency": "USD", "merchant_id": "m_acme001", "description": "order 1001"}


def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_create_and_fetch_payment():
    created = client.post("/payments", json=GOOD)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "authorized" and body["id"].startswith("pay_")
    fetched = client.get(f"/payments/{body['id']}")
    assert fetched.status_code == 200 and fetched.json()["amount"] == "125.50"


def test_list_is_scoped_to_merchant():
    client.post("/payments", json={**GOOD, "merchant_id": "m_other99"})
    rows = client.get("/payments", params={"merchant_id": "m_acme001"}).json()
    assert rows and all(r["merchant_id"] == "m_acme001" for r in rows)


def test_validation_rejects_bad_input():
    for bad in ({**GOOD, "amount": "-5"}, {**GOOD, "amount": "0.001"}, {**GOOD, "currency": "BTC"},
                {**GOOD, "merchant_id": "acme"}, {**GOOD, "description": "x" * 141}, {**GOOD, "role": "admin"}):
        assert client.post("/payments", json=bad).status_code == 422


def test_sql_injection_attempts_find_nothing():
    assert client.get("/payments/' OR '1'='1").status_code == 404
    assert client.get("/payments", params={"merchant_id": "m_acme001' OR '1'='1"}).status_code == 422


def test_security_headers_and_no_docs():
    r = client.get("/healthz")
    for header, value in SECURITY_HEADERS.items():
        assert r.headers[header] == value
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 200  # used by the DAST API scan
