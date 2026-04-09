# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseError
from opnsense.managers.auth_api_key import AuthApiKeyManager


@pytest.fixture
def mock_client() -> AsyncMock:
    from opnsense.client import OpnsenseClient

    client = AsyncMock(spec=OpnsenseClient)
    client._base_url = "https://opnsense.example.com"
    return client


@pytest.fixture
def mgr(mock_client: AsyncMock) -> AuthApiKeyManager:
    return AuthApiKeyManager(mock_client)


class TestListKeys:
    async def test_list_keys_returns_rows(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [
            {"key": "abc123", "id": "id-1", "username": "svc-test"},
            {"key": "def456", "id": "id-2", "username": "other"},
        ]
        result = await mgr.list_keys()
        mock_client.search.assert_awaited_once_with("auth/user/search_api_key/all")
        assert len(result) == 2

    async def test_list_keys_filtered_by_username(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [
            {"key": "abc123", "id": "id-1", "username": "svc-test"},
            {"key": "def456", "id": "id-2", "username": "other"},
        ]
        result = await mgr.list_keys(username="svc-test")
        assert len(result) == 1
        assert result[0]["username"] == "svc-test"

    async def test_list_keys_empty(self, mgr: AuthApiKeyManager, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        result = await mgr.list_keys()
        assert result == []


class TestCreateKey:
    async def test_create_key_success(self, mgr: AuthApiKeyManager, mock_client: AsyncMock) -> None:
        mock_client.post.return_value = {
            "result": "ok",
            "key": "new-key",
            "secret": "new-secret",
        }
        result = await mgr.create_key("svc-test")
        assert result.changed is True
        assert result.action == "created"
        assert result.after["key"] == "new-key"
        assert result.after["secret"] == "new-secret"
        assert result.after["username"] == "svc-test"
        mock_client.post.assert_awaited_once_with("auth/user/add_api_key/svc-test")

    async def test_create_key_check_mode(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        result = await mgr.create_key("svc-test", check_mode=True)
        assert result.changed is True
        assert result.action == "created"
        assert "<REDACTED:" in result.after["key"]
        mock_client.post.assert_not_awaited()

    async def test_create_key_failure_raises(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        mock_client.post.return_value = {"result": "failed"}
        with pytest.raises(OpnsenseError, match="Failed to create API key"):
            await mgr.create_key("nonexistent")


class TestDeleteKey:
    async def test_delete_key_success(self, mgr: AuthApiKeyManager, mock_client: AsyncMock) -> None:
        mock_client.post.return_value = {"result": "deleted"}
        result = await mgr.delete_key("base64-key-id")
        assert result.changed is True
        assert result.action == "deleted"
        mock_client.post.assert_awaited_once_with("auth/user/del_api_key/base64-key-id")

    async def test_delete_key_check_mode(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        result = await mgr.delete_key("base64-key-id", check_mode=True)
        assert result.changed is True
        assert result.action == "deleted"
        mock_client.post.assert_not_awaited()


class TestDeleteAllKeys:
    async def test_delete_all_keys_with_existing(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [
            {"key": "k1", "id": "id-1", "username": "svc-test"},
            {"key": "k2", "id": "id-2", "username": "svc-test"},
            {"key": "k3", "id": "id-3", "username": "other"},
        ]
        mock_client.post.return_value = {"result": "deleted"}
        result = await mgr.delete_all_keys("svc-test")
        assert result.changed is True
        assert result.action == "deleted"
        assert result.before["key_count"] == 2
        assert mock_client.post.await_count == 2

    async def test_delete_all_keys_none_exist(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [
            {"key": "k1", "id": "id-1", "username": "other"},
        ]
        result = await mgr.delete_all_keys("svc-test")
        assert result.changed is False
        assert result.action == "noop"

    async def test_delete_all_keys_check_mode(
        self, mgr: AuthApiKeyManager, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [
            {"key": "k1", "id": "id-1", "username": "svc-test"},
        ]
        result = await mgr.delete_all_keys("svc-test", check_mode=True)
        assert result.changed is True
        assert result.action == "deleted"
        mock_client.post.assert_not_awaited()
