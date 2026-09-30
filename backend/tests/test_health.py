import pytest
from pydantic import SecretStr, ValidationError

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


def test_prod_rejects_weak_secrets():
    with pytest.raises(ValidationError):
        Settings(app_env="prod", app_db_password=SecretStr("short"), jwt_secret=SecretStr("x" * 40))
    with pytest.raises(ValidationError):
        Settings(
            app_env="prod",
            app_db_password=SecretStr("a" * 40),
            jwt_secret=SecretStr("changeme" * 5),
        )


def test_prod_accepts_strong_secrets():
    s = Settings(
        app_env="prod", app_db_password=SecretStr("f3" * 24), jwt_secret=SecretStr("9a" * 32)
    )
    assert "f3f3" in s.database_url


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


def test_settings_errors_do_not_leak_secrets():
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="prod",
            app_db_password=SecretStr("leak-me-pw"),
            jwt_secret=SecretStr("leak-me-jwt"),
        )
    assert "leak-me" not in str(exc.value)
