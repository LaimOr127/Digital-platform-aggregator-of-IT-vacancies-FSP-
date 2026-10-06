"""Защита от SSRF для адресов языковых моделей.

Проверяется и запись адреса (схема, служебные имена стенда, IP-литералы), и то, куда имя
действительно резолвится перед каждым запросом: домен или десятичная запись IP, ведущие
на 127.0.0.1, метаданные облака или внутреннюю сеть, отклоняются. Частные сети
(on-prem модель, локальная Ollama) разрешаются только явно: AI_ALLOW_PRIVATE_NETWORK.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from app.core.errors import AppError

# сервисы стенда (docker compose): модель не может указывать на них
INTERNAL_HOSTS = {
    "db",
    "api",
    "worker",
    "web",
    "proxy",
    "migrate",
    "fsp-mock",
    "mailpit",
    "localhost",
}
_INTERNAL = "адрес указывает на внутренний сервис"


class UnsafeUrlError(AppError):
    status_code, code = 422, "unsafe_url"


def _blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, allow_private: bool) -> bool:
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast or ip.is_reserved:
        return True
    return ip.is_private and not allow_private


def check_url(url: str, allow_http: bool, allow_private: bool) -> str:
    """Проверка записи адреса (при сохранении): без обращения к сети."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise UnsafeUrlError("адрес модели должен начинаться с https://")
    if parts.scheme == "http" and not allow_http:
        raise UnsafeUrlError("нужен https:// (http разрешается только для локальной модели)")
    host = parts.hostname.lower()
    if host in INTERNAL_HOSTS:
        raise UnsafeUrlError(_INTERNAL)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url.strip().rstrip("/")
    if _blocked(ip, allow_private):
        raise UnsafeUrlError(_INTERNAL)
    return url.strip().rstrip("/")


async def ensure_public(url: str, allow_private: bool) -> None:
    """Перед запросом: все адреса, в которые резолвится имя, должны быть допустимы.
    Имя не резолвится — проверять нечего (запрос и так не уйдёт)."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, parts.port or 443)
    except socket.gaierror:
        return
    for info in infos:
        address = str(info[4][0]).split("%")[0]  # IPv6 с указанием интерфейса
        if _blocked(ipaddress.ip_address(address), allow_private):
            raise UnsafeUrlError(_INTERNAL)
