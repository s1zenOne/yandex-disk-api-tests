from __future__ import annotations

from uuid import uuid4

import pytest

from yandex_disk_api import YandexDiskClient

pytestmark = pytest.mark.integration


def child_path(root: str, label: str) -> str:
    return f"{root}/{label}-{uuid4().hex[:8]}"


def test_get_disk_information(disk_client: YandexDiskClient) -> None:
    response = disk_client.get_disk(fields="total_space,used_space,trash_size,system_folders")

    disk_client.expect_status(response, {200})
    payload = response.json()
    assert isinstance(payload["total_space"], int)
    assert isinstance(payload["used_space"], int)
    assert isinstance(payload["trash_size"], int)
    assert payload["total_space"] > 0
    assert payload["used_space"] >= 0
    assert payload["trash_size"] >= 0
    assert isinstance(payload["system_folders"], dict)


def test_get_resource_metadata(disk_client: YandexDiskClient, test_root: str) -> None:
    response = disk_client.get_resource(test_root, fields="name,path,type")

    disk_client.expect_status(response, {200})
    payload = response.json()
    assert payload["type"] == "dir"
    assert payload["path"].startswith("disk:")
    assert payload["name"] == test_root.rsplit("/", maxsplit=1)[-1]


def test_put_creates_directory(disk_client: YandexDiskClient, test_root: str) -> None:
    directory = child_path(test_root, "put")

    creation = disk_client.create_folder(directory)

    disk_client.expect_status(creation, {201})
    metadata = disk_client.get_resource(directory, fields="path,type")
    disk_client.expect_status(metadata, {200})
    assert metadata.json()["type"] == "dir"


def test_post_copies_resource(
    disk_client: YandexDiskClient,
    test_root: str,
    operation_timeout: float,
) -> None:
    source = child_path(test_root, "copy-source")
    destination = child_path(test_root, "copy-destination")
    disk_client.expect_status(disk_client.create_folder(source), {201})

    copy = disk_client.copy_resource(source, destination)

    disk_client.expect_status(copy, {201, 202})
    disk_client.wait_for_operation(copy, timeout=operation_timeout)
    metadata = disk_client.get_resource(destination, fields="path,type")
    disk_client.expect_status(metadata, {200})
    assert metadata.json()["type"] == "dir"


def test_delete_removes_resource(
    disk_client: YandexDiskClient,
    test_root: str,
    operation_timeout: float,
) -> None:
    directory = child_path(test_root, "delete")
    disk_client.expect_status(disk_client.create_folder(directory), {201})

    deletion = disk_client.delete_resource(directory, permanently=True)

    disk_client.expect_status(deletion, {202, 204})
    disk_client.wait_for_operation(deletion, timeout=operation_timeout)
    missing = disk_client.get_resource(directory)
    disk_client.expect_status(missing, {404})
    assert missing.json()["error"] == "DiskNotFoundError"
