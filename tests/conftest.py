from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest

from yandex_disk_api import DEFAULT_BASE_URL, YandexDiskClient


def pytest_report_header() -> str:
    token_state = "configured" if os.getenv("YANDEX_DISK_TOKEN") else "not configured"
    return f"Yandex Disk integration token: {token_state}"


@pytest.fixture(scope="session")
def disk_client() -> Iterator[YandexDiskClient]:
    token = os.getenv("YANDEX_DISK_TOKEN", "").strip()
    if not token:
        pytest.skip(
            "YANDEX_DISK_TOKEN is not set; use an OAuth token from a dedicated test account"
        )

    base_url = os.getenv("YANDEX_DISK_BASE_URL", DEFAULT_BASE_URL)
    timeout = float(os.getenv("YANDEX_DISK_TIMEOUT_SECONDS", "15"))
    with YandexDiskClient(token, base_url=base_url, timeout=timeout) as client:
        yield client


@pytest.fixture(scope="session")
def operation_timeout() -> float:
    return float(os.getenv("YANDEX_DISK_OPERATION_TIMEOUT_SECONDS", "30"))


@pytest.fixture(scope="session")
def test_root(disk_client: YandexDiskClient, operation_timeout: float) -> Iterator[str]:
    prefix = os.getenv("YANDEX_DISK_TEST_ROOT_PREFIX", "disk:/api-autotests").rstrip("/")
    if not prefix or prefix in {"disk:", "disk:/"}:
        pytest.fail("YANDEX_DISK_TEST_ROOT_PREFIX must point to a non-root test location")

    run_root = f"{prefix}-{uuid4().hex[:12]}"
    creation = disk_client.create_folder(run_root)
    disk_client.expect_status(creation, {201})

    try:
        yield run_root
    finally:
        deletion = disk_client.delete_resource(run_root, permanently=True)
        if deletion.status_code != 404:
            disk_client.expect_status(deletion, {202, 204})
            disk_client.wait_for_operation(deletion, timeout=operation_timeout)
