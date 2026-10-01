"""HttpFspClient: контракт с API ФСП, коды ответов, неожиданные ответы, безопасный путь."""

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import NotFoundError, RateLimitedError, ServiceUnavailableError
from app.integrations.fsp import FspVerificationError, HttpFspClient

SETTINGS = Settings(fsp_base_url="http://fsp", fsp_api_key=SecretStr("k" * 32))


def client_with(handler) -> HttpFspClient:
    return HttpFspClient(SETTINGS, transport=httpx.MockTransport(handler))


async def test_sends_api_key_and_parses_results():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers["X-Api-Key"]
        seen["path"] = request.url.path
        competition = {
            "discipline": "product",
            "title": "Ч",
            "level": "national",
            "date": "2025-01-01",
        }
        return httpx.Response(200, json=[{"id": "r1", "place": 2, "competition": competition}])

    (result,) = await client_with(handler).get_results("FSP-1")
    assert seen == {"key": "k" * 32, "path": "/api/v1/athletes/FSP-1/results"}
    assert (result.external_id, result.place, result.stage) == ("r1", 2, "final")


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (404, NotFoundError),
        (429, RateLimitedError),
        (400, FspVerificationError),
        (401, ServiceUnavailableError),
        (502, ServiceUnavailableError),
    ],
)
async def test_status_mapping(status: int, error: type[Exception]):
    client = client_with(lambda _: httpx.Response(status, json={"detail": "x"}))
    with pytest.raises(error):
        await client.confirm_verification("req", "123456")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>proxy error</html>"),
        httpx.Response(200, json={"unexpected": True}),
        httpx.Response(200, json=[{"id": "r1"}]),
    ],
)
async def test_unexpected_payload_is_unavailable_not_500(response: httpx.Response):
    client = client_with(lambda _: response)
    with pytest.raises(ServiceUnavailableError):
        await client.get_results("FSP-1")


async def test_network_error_is_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(ServiceUnavailableError):
        await client_with(handler).get_athlete("FSP-1")


@pytest.mark.parametrize("athlete_id", ["../admin", "FSP-1/../x", "a b"])
async def test_path_traversal_rejected_before_request(athlete_id: str):
    called = []
    client = client_with(lambda r: called.append(r) or httpx.Response(200, json={}))
    with pytest.raises(NotFoundError):
        await client.get_athlete(athlete_id)
    assert called == []


async def test_start_verification_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/verification/start"
        return httpx.Response(
            200, json={"request_id": "r", "email_masked": "a***@x", "expires_in": 600}
        )

    started = await client_with(handler).start_verification("FSP-1")
    assert (started.request_id, started.demo_code) == ("r", None)
