"""TOTP (RFC 6238): эталонные векторы, окно допуска, защита от повторного кода."""

import base64

import pytest

from app.core.totp import code_at, generate_secret, provisioning_uri, verify

# RFC 6238, приложение B: секрет "12345678901234567890" (SHA1), последние 6 цифр
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()


@pytest.mark.parametrize(
    ("timestamp", "code"),
    [(59, "287082"), (1111111109, "081804"), (1111111111, "050471"), (1234567890, "005924")],
)
def test_rfc6238_vectors(timestamp: int, code: str):
    assert code_at(RFC_SECRET, timestamp // 30) == code


def test_accepts_adjacent_step_and_returns_it():
    now = 1111111111
    previous = code_at(RFC_SECRET, now // 30 - 1)
    assert verify(RFC_SECRET, previous, now, last_step=None) == now // 30 - 1


def test_rejects_wrong_and_far_codes():
    now = 1111111111
    assert verify(RFC_SECRET, "000000", now, None) is None
    assert verify(RFC_SECRET, code_at(RFC_SECRET, now // 30 - 3), now, None) is None
    assert verify(RFC_SECRET, "12345", now, None) is None
    assert verify(RFC_SECRET, "abcdef", now, None) is None


def test_replay_of_used_code_rejected():
    now = 1111111111
    code = code_at(RFC_SECRET, now // 30)
    step = verify(RFC_SECRET, code, now, None)
    assert step is not None
    assert verify(RFC_SECRET, code, now, last_step=step) is None


def test_secret_and_uri():
    secret = generate_secret()
    assert len(base64.b32decode(secret)) == 20
    uri = provisioning_uri(secret, "admin@example.org", "IT Match")
    assert uri.startswith("otpauth://totp/IT%20Match:admin%40example.org?")
    assert f"secret={secret}" in uri and "issuer=IT%20Match" in uri
