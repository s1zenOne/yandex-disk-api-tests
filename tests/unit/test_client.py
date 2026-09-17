from __future__ import annotations

import json
from collections import deque
from typing import Any

import pytest
import requests

from yandex_disk_api import (
    OperationFailedError,
    YandexDiskAPIError,
    YandexDiskClient,
)


def response(status: int = 200, payload: dict[str, Any] | None = None) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result.url = "https://cloud-api.yandex.net/v1/disk/test"
    result._content = json.dumps(payload or {}).encode()  # noqa: SLF001
    result.headers["Content-Type"] = "application/json"
    return result


class FakeSession:
    def __init__(self, responses: list[requests.Response] | None = None) -> None:
        self.headers: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []
        self.responses = deque(responses or [])
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.popleft() if self.responses else response()

    def close(self) -> None:
        self.closed = True


def test_client_sends_oauth_header_and_expected_http_methods() -> None:
    session = FakeSession()
    client = YandexDiskClient("secret-token", session=session)  # type: ignore[arg-type]

    client.get_disk(fields="total_space")
    client.get_resource("disk:/folder")
    client.create_folder("disk:/folder")
    client.copy_resource("disk:/source", "disk:/destination")
    client.delete_resource("disk:/folder")

    assert session.headers["Authorization"] == "OAuth secret-token"
    assert [call["method"] for call in session.calls] == ["GET", "GET", "PUT", "POST", "DELETE"]
    assert session.calls[0]["url"] == "https://cloud-api.yandex.net/v1/disk"
    assert session.calls[3]["url"].endswith("/resources/copy")
    assert session.calls[3]["params"]["overwrite"] == "false"
    assert session.calls[4]["params"]["permanently"] == "true"


def test_wait_for_operation_polls_until_success() -> None:
    session = FakeSession(
        [
            response(payload={"status": "in-progress"}),
            response(payload={"status": "success"}),
        ]
    )
    client = YandexDiskClient("token", session=session)  # type: ignore[arg-type]
    accepted = response(202, {"href": "https://cloud-api.yandex.net/v1/disk/operations/42"})

    result = client.wait_for_operation(accepted, timeout=1, interval=0)

    assert result == {"status": "success"}
    assert len(session.calls) == 2
    assert all(call["method"] == "GET" for call in session.calls)


def test_wait_for_operation_raises_on_failed_status() -> None:
    session = FakeSession([response(payload={"status": "failed"})])
    client = YandexDiskClient("token", session=session)  # type: ignore[arg-type]
    accepted = response(202, {"href": "https://cloud-api.yandex.net/v1/disk/operations/42"})

    with pytest.raises(OperationFailedError, match="operation failed"):
        client.wait_for_operation(accepted, timeout=1, interval=0)


def test_unexpected_response_error_does_not_include_oauth_token() -> None:
    failure = response(401, {"error": "UnauthorizedError"})

    with pytest.raises(YandexDiskAPIError) as error:
        YandexDiskClient.expect_status(failure, {200})

    assert "secret-token" not in str(error.value)
    assert "HTTP 401" in str(error.value)


@pytest.mark.parametrize("token", ["", "   "])
def test_client_rejects_empty_token(token: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        YandexDiskClient(token)
