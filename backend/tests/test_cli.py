"""Служебные команды CLI: администраторы (единственный способ получить роль admin), 2FA, почта."""

import pytest
from sqlalchemy import select

from app import cli
from app.models import AuditLog, User
from tests.helpers import PASSWORD, login, unique_email


def _fake_getpass(*answers: str):
    replies = iter(answers)
    return lambda _prompt="": next(replies)


def test_read_password_mismatch_exits(monkeypatch):
    monkeypatch.setattr(cli.getpass, "getpass", _fake_getpass("Str0ng-pass-42", "other-pass-42"))
    with pytest.raises(SystemExit, match="не совпадают"):
        cli._read_password()


def test_read_password_rejects_weak(monkeypatch):
    monkeypatch.setattr(cli.getpass, "getpass", _fake_getpass("1234567890", "1234567890"))
    with pytest.raises(SystemExit, match="слабый пароль"):
        cli._read_password()


def test_read_password_accepts_strong(monkeypatch):
    monkeypatch.setattr(cli.getpass, "getpass", _fake_getpass("Str0ng-pass-42", "Str0ng-pass-42"))
    assert cli._read_password() == "Str0ng-pass-42"


def test_validate_email():
    assert cli._validate_email("Root@Example.org") == "Root@example.org"
    with pytest.raises(SystemExit, match="некорректный email"):
        cli._validate_email("not-an-email")


async def test_create_superadmin(monkeypatch, db, capsys):
    monkeypatch.setattr(cli, "get_database", lambda: db)
    monkeypatch.setattr(db, "dispose", _noop)
    await cli.create_admin("root@example.org", "Str0ng-pass-42", superadmin=True)
    async with db.sessionmaker() as session:
        user = (await session.execute(select(User))).scalar_one()
    assert user.role == "admin" and user.is_superadmin and not user.totp_enabled
    assert user.email_verified  # адрес задаёт оператор: письмо подтверждения не нужно
    out = capsys.readouterr().out
    assert "admin created" in out and "2fa enrollment code" in out


async def test_reset_2fa_prints_new_code_and_rejects_unknown(monkeypatch, db, capsys):
    monkeypatch.setattr(cli, "get_database", lambda: db)
    monkeypatch.setattr(db, "dispose", _noop)
    await cli.create_admin("ops@example.org", "Str0ng-pass-42", superadmin=False)
    first = capsys.readouterr().out.rsplit(" ", 1)[-1].strip()
    await cli.reset_admin_mfa("ops@example.org")
    second = capsys.readouterr().out.rsplit(" ", 1)[-1].strip()
    assert first and second and first != second
    with pytest.raises(SystemExit, match="администратор не найден"):
        await cli.reset_admin_mfa("nobody@example.org")


async def test_confirm_email_lets_user_sign_in(monkeypatch, db, client, capsys):
    """Стенд без SMTP: пользователь регистрируется сам, оператор подтверждает адрес."""
    monkeypatch.setattr(cli, "get_database", lambda: db)
    monkeypatch.setattr(db, "dispose", _noop)
    email = unique_email("nomail")
    await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": email, "password": PASSWORD, "full_name": "Анна"},
    )
    await cli.confirm_email(email.upper())
    assert "email confirmed" in capsys.readouterr().out
    assert await login(client, email)
    async with db.sessionmaker() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "auth.email_confirmed_by_operator" in actions
    with pytest.raises(SystemExit, match="не найден"):
        await cli.confirm_email("nobody@example.org")


async def _noop() -> None:
    return None
