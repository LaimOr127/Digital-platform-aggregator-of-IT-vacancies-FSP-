"""Юнит-тесты изолированной логики: пароли, токены, шифрование, rate limit, курсоры."""

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.crypto import FieldCipher, profile_field_context
from app.core.errors import UnauthorizedError
from app.core.ratelimit import RateLimiter, client_ip, parse_rate
from app.core.security import TokenService, hash_password, hash_token, verify_password
from app.repositories.base import InvalidCursorError, decode_cursor, encode_cursor

SECRET = "a" * 64


@pytest.fixture
def tokens() -> TokenService:
    return TokenService(Settings(jwt_secret=SecretStr(SECRET)))


def test_password_hash_is_argon2id_and_verifies():
    h = hash_password("Str0ng-pass-42")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "Str0ng-pass-42")
    assert not verify_password(h, "wrong-pass-42")


def test_verify_password_without_user_is_false():
    assert not verify_password(None, "anything")


def test_refresh_token_stored_as_sha256():
    assert len(hash_token("x")) == 64 and hash_token("x") != "x"


def test_access_token_roundtrip(tokens: TokenService):
    uid = uuid.uuid4()
    claims = tokens.decode_access(tokens.issue_access(uid, "candidate"))
    assert claims.user_id == uid and claims.role == "candidate"


def test_access_token_tampered_signature_rejected(tokens: TokenService):
    token = tokens.issue_access(uuid.uuid4(), "candidate")
    forged = jwt.encode(jwt.decode(token, options={"verify_signature": False}), "other" * 10)
    with pytest.raises(UnauthorizedError):
        tokens.decode_access(forged)


def test_access_token_expired_rejected(tokens: TokenService):
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "admin", "typ": "access", "exp": past}, SECRET
    )
    with pytest.raises(UnauthorizedError):
        tokens.decode_access(token)


def test_alg_none_rejected(tokens: TokenService):
    token = jwt.encode({"sub": str(uuid.uuid4()), "role": "admin", "typ": "access"}, None, "none")
    with pytest.raises(UnauthorizedError):
        tokens.decode_access(token)


def test_token_service_requires_secret():
    with pytest.raises(RuntimeError):
        TokenService(Settings(jwt_secret=SecretStr("")))


CTX = profile_field_context("full_name", uuid.uuid4())


def test_cipher_roundtrip_and_random_nonce():
    cipher = FieldCipher("11" * 32)
    a, b = cipher.encrypt("Иван", CTX), cipher.encrypt("Иван", CTX)
    assert a != b and "Иван" not in a
    assert cipher.decrypt(a, CTX) == "Иван"
    assert cipher.encrypt(None, CTX) is None and cipher.decrypt(None, CTX) is None


def test_cipher_rejects_foreign_key():
    token = FieldCipher("11" * 32).encrypt("secret", CTX)
    with pytest.raises(ValueError):
        FieldCipher("22" * 32).decrypt(token, CTX)


def test_ciphertext_bound_to_field_and_owner():
    """Шифртекст, перенесённый в чужой профиль или другое поле, не расшифровывается."""
    cipher, owner = FieldCipher("11" * 32), uuid.uuid4()
    token = cipher.encrypt("+79990001122", profile_field_context("contacts", owner))
    with pytest.raises(ValueError):
        cipher.decrypt(token, profile_field_context("contacts", uuid.uuid4()))
    with pytest.raises(ValueError):
        cipher.decrypt(token, profile_field_context("full_name", owner))


def test_cipher_rejects_garbage():
    with pytest.raises(ValueError):
        FieldCipher("11" * 32).decrypt("not base64 !!", CTX)


@pytest.mark.parametrize("key", ["zz" * 32, "11" * 16])
def test_cipher_rejects_bad_key(key: str):
    with pytest.raises(RuntimeError):
        FieldCipher(key)


def test_rate_limiter_sliding_window():
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    assert all(limiter.hit("k", 3, 60) for _ in range(3))
    assert not limiter.hit("k", 3, 60)
    assert limiter.hit("other", 3, 60)
    now[0] = 61.0
    assert limiter.hit("k", 3, 60)


def test_rate_limiter_memory_bounded(monkeypatch):
    monkeypatch.setattr("app.core.ratelimit._MAX_KEYS", 10)
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    for i in range(50):
        now[0] = float(i)
        assert limiter.hit(f"ip-{i}", 5, 3600)
    assert len(limiter._hits) <= 10


def test_rate_limiter_eviction_respects_each_key_window(monkeypatch):
    """Очистка по короткому окну не сбрасывает часовые счётчики других областей."""
    monkeypatch.setattr("app.core.ratelimit._MAX_KEYS", 3)
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    assert limiter.hit("mfa:admin", 1, 3600)
    now[0] = 120.0
    assert limiter.hit("login:a", 5, 60)
    assert limiter.hit("login:b", 5, 60)
    now[0] = 200.0
    assert limiter.hit("login:c", 5, 60)  # переполнение: устаревают только минутные ключи
    assert not limiter.hit("mfa:admin", 1, 3600)


def test_client_ip_groups_ipv6_by_64():
    def request(host: str):
        return SimpleNamespace(client=SimpleNamespace(host=host))

    assert client_ip(request("203.0.113.7")) == "203.0.113.7"
    assert client_ip(request("2001:db8:1:2::a")) == client_ip(request("2001:db8:1:2:ffff::1"))
    assert client_ip(request("2001:db8:1:2::a")) == "2001:db8:1:2::/64"
    assert client_ip(request("testclient")) == "testclient"


def test_parse_rate():
    assert parse_rate("10/minute") == (10, 60)


def test_cursor_roundtrip_and_garbage():
    ts, rid = datetime.now(UTC), uuid.uuid4()
    assert decode_cursor(encode_cursor(ts, rid)) == (ts, rid)
    with pytest.raises(InvalidCursorError):
        decode_cursor("not-a-cursor")
