"""Small HTTP client used by the Yandex Disk API tests."""

from __future__ import annotations

import time
from collections.abc import Collection, Mapping
from typing import Any

import requests
from requests import Response, Session

DEFAULT_BASE_URL = "https://cloud-api.yandex.net/v1/disk"


class YandexDiskAPIError(RuntimeError):
    """Raised when the API returns an unexpected response."""


class OperationFailedError(YandexDiskAPIError):
    """Raised when an asynchronous Disk operation reports a failure."""


class OperationTimeoutError(YandexDiskAPIError):
    """Raised when an asynchronous Disk operation does not finish in time."""


class YandexDiskClient:
    """Minimal requests-based client for endpoints covered by the test project."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        session: Session | None = None,
    ) -> None:
        if not token.strip():
            raise ValueError("OAuth token must not be empty")
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"OAuth {token}",
                "User-Agent": "yandex-disk-api-tests/1.0",
            }
        )

    def __enter__(self) -> YandexDiskClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.session.close()

    def get_disk(self, *, fields: str | None = None) -> Response:
        """Return general information about the current user's Disk."""
        return self._request("GET", "", params=self._without_none(fields=fields))

    def get_resource(self, path: str, *, fields: str | None = None) -> Response:
        """Return metadata for a file or directory."""
        params = self._without_none(path=path, fields=fields)
        return self._request("GET", "resources", params=params)

    def create_folder(self, path: str) -> Response:
        """Create a directory with PUT /resources."""
        return self._request("PUT", "resources", params={"path": path})

    def copy_resource(
        self,
        from_path: str,
        path: str,
        *,
        overwrite: bool = False,
    ) -> Response:
        """Copy a resource with POST /resources/copy."""
        return self._request(
            "POST",
            "resources/copy",
            params={
                "from": from_path,
                "path": path,
                "overwrite": self._bool_param(overwrite),
            },
        )

    def delete_resource(self, path: str, *, permanently: bool = True) -> Response:
        """Delete a resource with DELETE /resources."""
        return self._request(
            "DELETE",
            "resources",
            params={"path": path, "permanently": self._bool_param(permanently)},
        )

    def wait_for_operation(
        self,
        operation_response: Response,
        *,
        timeout: float = 30.0,
        interval: float = 0.5,
    ) -> Mapping[str, Any] | None:
        """Wait for a 202 response operation; return immediately for synchronous responses."""
        if operation_response.status_code != 202:
            return None

        self.expect_status(operation_response, {202})
        payload = self._json_object(operation_response)
        href = payload.get("href") or operation_response.headers.get("Location")
        if not isinstance(href, str) or not href:
            raise YandexDiskAPIError("The asynchronous response does not contain an operation URL")

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self._request("GET", href)
            self.expect_status(response, {200})
            operation = self._json_object(response)
            status = operation.get("status")

            if status == "success":
                return operation
            if status == "failed":
                raise OperationFailedError(f"Yandex Disk operation failed: {operation!r}")
            if status != "in-progress":
                raise YandexDiskAPIError(f"Unknown Yandex Disk operation status: {status!r}")

            time.sleep(interval)

        raise OperationTimeoutError(f"Yandex Disk operation did not finish in {timeout:g} seconds")

    @staticmethod
    def expect_status(response: Response, expected: Collection[int]) -> None:
        """Raise a concise error without exposing authorization headers."""
        if response.status_code in expected:
            return

        body = response.text[:500]
        expected_text = ", ".join(str(code) for code in sorted(expected))
        raise YandexDiskAPIError(
            f"Unexpected HTTP {response.status_code}; expected {expected_text}; "
            f"url={response.url!r}; body={body!r}"
        )

    def _request(
        self,
        method: str,
        endpoint_or_url: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        url = self._url(endpoint_or_url)
        return self.session.request(method, url, params=params, timeout=self.timeout)

    def _url(self, endpoint_or_url: str) -> str:
        if endpoint_or_url.startswith(("https://", "http://")):
            return endpoint_or_url
        if not endpoint_or_url:
            return self.base_url
        return f"{self.base_url}/{endpoint_or_url.lstrip('/')}"

    @staticmethod
    def _bool_param(value: bool) -> str:
        return str(value).lower()

    @staticmethod
    def _without_none(**values: str | None) -> dict[str, str]:
        return {key: value for key, value in values.items() if value is not None}

    @staticmethod
    def _json_object(response: Response) -> Mapping[str, Any]:
        try:
            payload = response.json()
        except requests.JSONDecodeError as error:
            raise YandexDiskAPIError("Yandex Disk returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise YandexDiskAPIError("Yandex Disk returned JSON with an unexpected shape")
        return payload
