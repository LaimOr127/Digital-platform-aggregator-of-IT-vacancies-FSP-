import pytest
from fastapi.testclient import TestClient

import app.main as mock
from app.verification import MAX_ATTEMPTS, VerificationError, VerificationStore

KEY = "test-key"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(mock, "API_KEY", KEY)
    monkeypatch.setattr(mock, "EXPOSE_CODES", True)
    mock.app.state.verification = VerificationStore()
    return TestClient(mock.app, headers={"X-Api-Key": KEY})


def test_requires_api_key(client):
    r = TestClient(mock.app).get("/api/v1/disciplines")
    assert r.status_code == 401
    assert client.get("/api/v1/disciplines").status_code == 200


def test_athlete_and_results(client):
    assert client.get("/api/v1/athletes/fsp-24002").json()["rank"] == "МС"
    results = client.get("/api/v1/athletes/FSP-24002/results").json()
    assert {r["competition"]["level"] for r in results} == {"international", "national", "regional"}
    assert client.get("/api/v1/athletes/FSP-00000").status_code == 404


def test_athlete_payload_hides_email(client):
    assert "email" not in client.get("/api/v1/athletes/FSP-24001").json()


def test_verification_flow(client):
    start = client.post("/api/v1/verification/start", json={"athlete_id": "FSP-24001"}).json()
    assert start["email_masked"].startswith("a") and "*" in start["email_masked"]
    wrong = "000000" if start["demo_code"] != "000000" else "111111"
    bad = client.post(
        "/api/v1/verification/confirm", json={"request_id": start["request_id"], "code": wrong}
    )
    assert bad.status_code == 400
    ok = client.post(
        "/api/v1/verification/confirm",
        json={"request_id": start["request_id"], "code": start["demo_code"]},
    )
    assert ok.json() == {"athlete_id": "FSP-24001"}
    again = client.post(
        "/api/v1/verification/confirm",
        json={"request_id": start["request_id"], "code": start["demo_code"]},
    )
    assert again.status_code == 400  # код одноразовый


def test_code_hidden_unless_exposed(client, monkeypatch):
    monkeypatch.setattr(mock, "EXPOSE_CODES", False)
    start = client.post("/api/v1/verification/start", json={"athlete_id": "FSP-24001"}).json()
    assert "demo_code" not in start


def test_attempts_limited():
    store = VerificationStore()
    request_id, code = store.start("FSP-24001")
    wrong = "111111" if code != "111111" else "222222"
    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(VerificationError):
            store.confirm(request_id, wrong)
    with pytest.raises(VerificationError) as exc:
        store.confirm(request_id, code)
    assert exc.value.status == 429


def test_code_expires():
    now = [0.0]
    store = VerificationStore(clock=lambda: now[0])
    request_id, code = store.start("FSP-24001")
    now[0] = 601
    with pytest.raises(VerificationError, match="expired"):
        store.confirm(request_id, code)


def test_new_code_invalidates_previous_request():
    store = VerificationStore()
    first, code = store.start("FSP-24001")
    store.start("FSP-24001")
    with pytest.raises(VerificationError, match="expired"):
        store.confirm(first, code)


def test_daily_failure_cap_per_athlete():
    """Перебор через новые запросы кода упирается в суточный лимит неудач на аккаунт."""
    from app.verification import MAX_DAILY_FAILURES

    now = [0.0]
    store = VerificationStore(clock=lambda: now[0])
    failures = 0
    while failures < MAX_DAILY_FAILURES:
        request_id, code = store.start("FSP-24001")
        wrong = "111111" if code != "111111" else "222222"
        with pytest.raises(VerificationError):
            store.confirm(request_id, wrong)
        failures += 1
    with pytest.raises(VerificationError) as exc:
        store.start("FSP-24001")
    assert exc.value.status == 429
    now[0] = 86_401  # через сутки лимит снимается
    assert store.start("FSP-24001")


def test_mask_hides_name_length():
    from app.data import mask_email

    assert mask_email("ab@x.ru") == "a***@x.ru"
    assert mask_email("anna.smirnova@example.org") == "a***@example.org"
