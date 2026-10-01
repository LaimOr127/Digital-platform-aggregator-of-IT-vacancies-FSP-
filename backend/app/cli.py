"""Служебные команды. Первый суперадмин создаётся только так (через API — нельзя):

    make create-admin EMAIL=admin@example.org
    make reset-admin-2fa EMAIL=admin@example.org

Пароль запрашивается интерактивно (не попадает в историю shell и в логи).
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import get_settings
from app.core.crypto import FieldCipher
from app.core.errors import NotFoundError
from app.core.security import TokenService
from app.db.demo import seed_candidates
from app.db.session import get_database
from app.schemas.auth import PasswordMixin
from app.services.auth import AuthService
from app.services.enrollment import ENROLL_TTL
from app.services.mfa import reset_mfa


async def create_admin(email: str, password: str, superadmin: bool) -> None:
    settings = get_settings()
    db = get_database()
    try:
        async with db.sessionmaker() as session:
            service = AuthService(
                session,
                TokenService(settings),
                FieldCipher(settings.secret("field_encryption_key")),
            )
            user, code = await service.create_admin(email, password, superadmin)
    finally:
        await db.dispose()
    sys.stdout.write(f"admin created: {user.id}\n")
    _print_enrollment(code)


async def reset_admin_mfa(email: str) -> None:
    """Сброс 2FA администратора (потерян телефон): при следующем входе — новая настройка."""
    db = get_database()
    try:
        async with db.sessionmaker() as session:
            code = await reset_mfa(session, email)
    except NotFoundError as exc:
        sys.exit(exc.message)
    finally:
        await db.dispose()
    sys.stdout.write("2fa reset: sessions revoked\n")
    _print_enrollment(code)


def _print_enrollment(code: str) -> None:
    """Код подключения 2FA показывается один раз — передайте его администратору лично."""
    sys.stdout.write(
        f"2fa enrollment code (valid {ENROLL_TTL.total_seconds() // 3600:.0f}h, one-time): {code}\n"
    )


async def seed_demo(count: int) -> None:
    settings = get_settings()
    if settings.is_prod:
        sys.exit("демо-данные не создаются в prod")
    if not 1 <= count <= 20_000:
        sys.exit("--candidates: от 1 до 20000")
    db = get_database()
    try:
        async with db.sessionmaker() as session:
            cipher = FieldCipher(settings.secret("field_encryption_key"))
            created = await seed_candidates(session, cipher, count)
    finally:
        await db.dispose()
    sys.stdout.write(f"demo candidates created: {created}\n")


def _validate_email(email: str) -> str:
    try:
        return str(TypeAdapter(EmailStr).validate_python(email))
    except ValidationError:
        sys.exit(f"некорректный email: {email}")


def _read_password() -> str:
    password = getpass.getpass("Пароль: ")
    if password != getpass.getpass("Повторите пароль: "):
        sys.exit("пароли не совпадают")
    try:
        PasswordMixin(password=password)
    except ValidationError as exc:
        sys.exit(f"слабый пароль: {exc.errors()[0]['msg']}")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="создать администратора")
    admin.add_argument("--email", required=True)
    admin.add_argument("--superadmin", action="store_true")
    reset = sub.add_parser("reset-2fa", help="сбросить 2FA администратора")
    reset.add_argument("--email", required=True)
    demo = sub.add_parser("seed-demo", help="демо-кандидаты для каталога (только dev)")
    demo.add_argument("--candidates", type=int, default=500)
    args = parser.parse_args()
    if args.command == "seed-demo":
        asyncio.run(seed_demo(args.candidates))
        return
    email = _validate_email(args.email)
    if args.command == "create-admin":
        asyncio.run(create_admin(email, _read_password(), args.superadmin))
    elif args.command == "reset-2fa":
        asyncio.run(reset_admin_mfa(email))


if __name__ == "__main__":
    main()
