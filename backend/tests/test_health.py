import pytest
from pydantic import SecretStr

from app.core.config import Settings


def test_liveness(make_client):
    r = make_client().get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_when_db_up(make_client):
    assert make_client(db_alive=True).get("/api/v1/health/ready").status_code == 200


def test_ready_when_db_down_uses_error_format(make_client):
    r = make_client(db_alive=False).get("/api/v1/health/ready")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"


def test_unknown_route_uses_error_format(make_client):
    r = make_client().get("/api/v1/nope")
    assert r.status_code == 404
    assert "error" in r.json()


@pytest.mark.parametrize("value", ["short", "changeme" * 5, ""])
def test_prod_rejects_weak_secret_on_use(value: str):
    settings = Settings(app_env="prod", jwt_secret=SecretStr(value))
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        settings.secret("jwt_secret")


def test_prod_checks_only_used_secrets():
    """migrate получает только пароль владельца: отсутствие JWT_SECRET ему не мешает."""
    settings = Settings(app_env="prod", db_owner_user="o", db_owner_password=SecretStr("ab" * 20))
    assert "abab" in settings.migration_database_url


def test_dev_allows_empty_secrets():
    assert Settings(app_env="dev", jwt_secret=SecretStr("")).secret("jwt_secret") == ""


def test_prod_accepts_strong_secrets():
    s = Settings(app_env="prod", app_db_password=SecretStr("f3" * 24))
    assert "f3f3" in s.database_url


def test_database_url_escapes_password():
    s = Settings(app_db_password=SecretStr("p@ss:w/rd%#"))
    assert "p%40ss%3Aw%2Frd%25%23@db:5432/itmatch" in s.database_url


def test_log_redaction():
    import logging

    from app.core.logging import RedactingFilter

    rec = logging.LogRecord("t", 20, "", 0, "password=hunter2 token: abc", None, None)
    RedactingFilter().filter(rec)
    assert "hunter2" not in rec.msg and "abc" not in rec.msg


def test_log_redaction_keeps_non_string_args():
    import logging

    from app.core.logging import RedactingFilter

    rec = logging.LogRecord("t", 20, "", 0, "starting %d job(s), %s", (3, "token=abc"), None)
    RedactingFilter().filter(rec)
    assert rec.getMessage() == "starting 3 job(s), token=***"


def test_weak_secret_error_does_not_leak_value():
    settings = Settings(app_env="prod", jwt_secret=SecretStr("leak-me-jwt"))
    with pytest.raises(RuntimeError) as exc:
        settings.secret("jwt_secret")
    assert "leak-me" not in str(exc.value)


def test_integrity_error_becomes_409_without_sql_details():
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import IntegrityError

    from app.main import create_app

    app = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise IntegrityError("INSERT INTO users ... secret@example.org", {}, Exception("dup"))

    r = TestClient(app).get("/boom")
    assert r.status_code == 409 and "secret@" not in r.text


def test_openapi_documents_error_responses(make_client):
    """Каждый маршрут описывает коды ошибок единой схемой ErrorOut (ТЗ 3.5: «коды ошибок»)."""
    spec = make_client().get("/api/openapi.json").json()
    assert set(spec["components"]["schemas"]["ErrorOut"]["properties"]) == {"error"}
    operation = spec["paths"]["/api/v1/employer/applications"]["post"]
    for status in ("400", "401", "403", "404", "409", "422", "429"):
        schema = operation["responses"][status]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/ErrorOut"}
