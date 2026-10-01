"""TOTP (RFC 6238, HMAC-SHA1, 30 с, 6 цифр) для двухфакторного входа администраторов.

Допуск ±1 шаг (рассинхрон часов), повторное использование уже принятого кода запрещено:
вызывающий хранит последний принятый шаг и передаёт его в verify.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode()


def code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def verify(secret: str, code: str, now: float, last_step: int | None) -> int | None:
    """Шаг, которому соответствует код, или None. Шаги не новее last_step не принимаются."""
    if len(code) != DIGITS or not code.isdigit():
        return None
    current = int(now) // STEP_SECONDS
    for step in range(current - WINDOW, current + WINDOW + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    """otpauth:// для QR-кода в приложении-аутентификаторе."""
    label = quote(f"{issuer}:{account}", safe=":")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP_SECONDS}"
