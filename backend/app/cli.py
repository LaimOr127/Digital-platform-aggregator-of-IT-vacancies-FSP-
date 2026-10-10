"""Служебные команды. Первый суперадмин создаётся только так (через API — нельзя):

    make create-admin EMAIL=admin@example.org
    make reset-admin-2fa EMAIL=admin@example.org
    make confirm-email EMAIL=user@example.org   # письмо не дошло: подтвердить адрес вручную

Пароль запрашивается интерактивно (не попадает в историю shell и в логи).
"""

import argparse
import asyncio
import getpass
import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import get_settings
from app.core.crypto import FieldCipher
from app.core.errors import NotFoundError
from app.core.security import TokenService
from app.db.demo import seed_candidates, seed_market
from app.db.demo_logins import seed_logins
from app.db.session import get_database
from app.schemas.auth import PasswordMixin
from app.services.account import AccountService
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


async def confirm_email(email: str) -> None:
    settings = get_settings()
    db = get_database()
    try:
        async with db.sessionmaker() as session:
            cipher = FieldCipher(settings.secret("field_encryption_key"))
            await AccountService(session, cipher).confirm_email_by_operator(email)
    except NotFoundError as exc:
        sys.exit(exc.message)
    finally:
        await db.dispose()
    sys.stdout.write("email confirmed\n")


def _print_enrollment(code: str) -> None:
    """Код подключения 2FA показывается один раз — передайте его администратору лично."""
    sys.stdout.write(
        f"2fa enrollment code (valid {ENROLL_TTL.total_seconds() // 3600:.0f}h, one-time): {code}\n"
    )


async def seed_demo(count: int, companies: int, vacancies_each: int, stand: bool = False) -> None:
    settings = get_settings()
    if settings.is_prod and not stand:
        sys.exit("в prod демо-данные заливаются только явно: --stand (make seed-demo STAND=1)")
    if not 0 <= count <= 20_000 or not 0 <= companies <= 200 or not 0 <= vacancies_each <= 50:
        sys.exit("лимиты: --candidates до 20000, --companies до 200, --vacancies до 50")
    db = get_database()
    try:
        async with db.sessionmaker() as session:
            cipher = FieldCipher(settings.secret("field_encryption_key"))
            created = await seed_candidates(session, cipher, count) if count else 0
            vacancies = await seed_market(session, companies, vacancies_each) if companies else 0
            # пароль демо-входов: DEMO_PASSWORD (чтобы вписать в памятку жюри) или случайный
            logins = await seed_logins(session, cipher, os.environ.get("DEMO_PASSWORD") or None)
    finally:
        await db.dispose()
    sys.stdout.write(f"demo candidates: {created}, demo vacancies: {vacancies}\n")
    # пароль показывается один раз — как код подключения 2FA у create-admin
    for email, password in logins.items():
        sys.stdout.write(f"demo login: {email} / {password}\n")


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
    confirm = sub.add_parser("confirm-email", help="подтвердить почту пользователя вручную")
    confirm.add_argument("--email", required=True)
    demo = sub.add_parser("seed-demo", help="демо-данные: dev; на стенде жюри — с --stand")
    demo.add_argument("--candidates", type=int, default=500)
    demo.add_argument("--companies", type=int, default=6)
    demo.add_argument("--vacancies", type=int, default=8, help="вакансий у каждой компании")
    demo.add_argument("--stand", action="store_true", help="разрешить на prod-стенде для жюри")
    args = parser.parse_args()
    if args.command == "seed-demo":
        asyncio.run(seed_demo(args.candidates, args.companies, args.vacancies, args.stand))
        return
    email = _validate_email(args.email)
    if args.command == "create-admin":
        asyncio.run(create_admin(email, _read_password(), args.superadmin))
    elif args.command == "reset-2fa":
        asyncio.run(reset_admin_mfa(email))
    elif args.command == "confirm-email":
        asyncio.run(confirm_email(email))


if __name__ == "__main__":
    main()
