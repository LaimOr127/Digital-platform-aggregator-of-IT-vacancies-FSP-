"""Шифрование персональных данных на уровне приложения (AES-256-GCM).

Формат значения в БД: base64(nonce[12] + ciphertext + tag).
Ключ — FIELD_ENCRYPTION_KEY (hex, 32 байта). Контекст (AAD) привязывает шифртекст к полю и
владельцу: перенос значения в чужую строку или другую колонку не расшифруется.
"""

import base64
import os
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LEN = 12


def profile_field_context(field: str, user_id: uuid.UUID) -> bytes:
    return f"candidate_profiles.{field}:{user_id}".encode()


def user_field_context(field: str, user_id: uuid.UUID) -> bytes:
    return f"users.{field}:{user_id}".encode()


def offer_field_context(field: str, offer_id: uuid.UUID) -> bytes:
    return f"offers.{field}:{offer_id}".encode()


def ai_key_context(provider_id: uuid.UUID) -> bytes:
    return f"ai_providers.api_key:{provider_id}".encode()


def outbox_payload_context(message_id: uuid.UUID) -> bytes:
    return f"outbox.payload:{message_id}".encode()


class FieldCipher:
    def __init__(self, hex_key: str) -> None:
        try:
            key = bytes.fromhex(hex_key)
        except ValueError as exc:
            msg = "FIELD_ENCRYPTION_KEY должен быть hex-строкой"
            raise RuntimeError(msg) from exc
        if len(key) != 32:
            msg = "FIELD_ENCRYPTION_KEY должен содержать 32 байта (64 hex-символа)"
            raise RuntimeError(msg)
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: str | None, context: bytes) -> str | None:
        if plaintext is None:
            return None
        nonce = os.urandom(_NONCE_LEN)
        sealed = self._aead.encrypt(nonce, plaintext.encode(), context)
        return base64.b64encode(nonce + sealed).decode()

    def decrypt(self, token: str | None, context: bytes) -> str | None:
        if token is None:
            return None
        try:
            raw = base64.b64decode(token, validate=True)
            return self._aead.decrypt(raw[:_NONCE_LEN], raw[_NONCE_LEN:], context).decode()
        except (InvalidTag, ValueError) as exc:
            msg = "повреждённые или чужие зашифрованные данные"
            raise ValueError(msg) from exc
