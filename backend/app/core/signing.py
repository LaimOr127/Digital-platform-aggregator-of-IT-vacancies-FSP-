"""Подпись паспорта навыков (Ed25519). Любой может проверить подлинность по публичному ключу,
не доверяя серверу: подпись покрывает каноничный JSON содержимого паспорта."""

import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def canonical_json(payload: dict) -> bytes:
    """Детерминированная сериализация: одинаковые данные — одинаковые байты."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class PassportSigner:
    def __init__(self, hex_seed: str) -> None:
        try:
            seed = bytes.fromhex(hex_seed)
        except ValueError as exc:
            msg = "PASSPORT_SIGNING_KEY должен быть hex-строкой"
            raise RuntimeError(msg) from exc
        if len(seed) != 32:
            msg = "PASSPORT_SIGNING_KEY должен содержать 32 байта (64 hex-символа)"
            raise RuntimeError(msg)
        self._private = Ed25519PrivateKey.from_private_bytes(seed)
        self._public = self._private.public_key()
        raw = self._public.public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.public_key_b64 = base64.b64encode(raw).decode()
        self.key_id = hashlib.sha256(raw).hexdigest()[:16]

    def sign(self, payload: dict) -> str:
        return base64.b64encode(self._private.sign(canonical_json(payload))).decode()

    def verify(self, payload: dict, signature_b64: str) -> bool:
        try:
            self._public.verify(base64.b64decode(signature_b64), canonical_json(payload))
        except (InvalidSignature, ValueError):
            return False
        return True
