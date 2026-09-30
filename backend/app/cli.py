"""Служебные команды. Первый суперадмин создаётся только так (через API — нельзя):

    make create-admin EMAIL=admin@example.org

Пароль запрашивается интерактивно (не попадает в историю shell и в логи).
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import get_settings
from app.core.crypto import FieldCipher
from app.core.security import TokenService
from app.db.session import get_database
from app.schemas.auth import PasswordMixin
from app.services.auth import AuthService


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
            user = await service.create_admin(email, password, superadmin)
    finally:
        await db.dispose()
    sys.stdout.write(f"admin created: {user.id}\n")


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
    args = parser.parse_args()
    if args.command == "create-admin":
        email = _validate_email(args.email)
        asyncio.run(create_admin(email, _read_password(), args.superadmin))


if __name__ == "__main__":
    main()
