"""CLI создания администратора: единственный способ получить роль admin."""

import pytest
from sqlalchemy import select

from app import cli
from app.models import User


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
    assert user.role == "admin" and user.is_superadmin
    assert "admin created" in capsys.readouterr().out


async def _noop() -> None:
    return None
