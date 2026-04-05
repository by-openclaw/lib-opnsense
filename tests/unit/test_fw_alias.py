"""Unit tests for opnsense.managers.fw_alias.FwAliasManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseError, OpnsenseValidationError
from opnsense.managers.fw_alias import FwAliasManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_alias(self, mock_client: AsyncMock) -> None:
        """ensure present when alias does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "net_dmz", "type": "network", "content": "10.6.225.0/24"},
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/alias/reconfigure")

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when alias exists with matching params -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24",
            },
        ]

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-existing"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when alias content differs -> update + reconfigure."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24",
            },
        ]
        mock_client.get.return_value = {
            "alias": {
                "uuid": "uuid-existing",
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24\n10.6.226.0/24",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/alias/reconfigure")


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_alias(self, mock_client: AsyncMock) -> None:
        """ensure absent when alias exists -> delete + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "net_dmz"},
        ]
        mock_client.get.return_value = {
            "alias": {"uuid": "uuid-existing", "name": "net_dmz"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "net_dmz"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/alias/reconfigure")

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when alias does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no API calls."""
        mock_client.search.return_value = []

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "net_test", "type": "host"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Item entity suffix."""

    async def test_search_uses_search_item(self, mock_client: AsyncMock) -> None:
        """list() calls search endpoint with Item suffix."""
        mock_client.search.return_value = []

        mgr = FwAliasManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with("firewall/alias/searchItem", search_phrase="")

    async def test_create_uses_add_item(self, mock_client: AsyncMock) -> None:
        """create() calls add endpoint with Item suffix."""
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwAliasManager(mock_client)
        await mgr.create(params={"name": "test", "type": "host"})

        mock_client.create.assert_awaited_once_with(
            "firewall/alias/addItem", "alias", {"name": "test", "type": "host"}
        )


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on FwAliasManager."""

    async def test_redact_fields_defined(self) -> None:
        """FwAliasManager redacts password and username (URL table auth)."""
        assert "password" in FwAliasManager.REDACT_FIELDS
        assert "username" in FwAliasManager.REDACT_FIELDS

    async def test_create_redacts_password_in_result(self, mock_client: AsyncMock) -> None:
        """ensure present create -> password is redacted in after dict."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "url_feed", "type": "urltable", "password": "s3cret"},
        )

        assert result.after is not None
        assert result.after["password"] == "<REDACTED:password>"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When create() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="name already exists", endpoint="firewall/alias/addItem"
        )

        mgr = FwAliasManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"name": "dup"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When delete() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = [{"uuid": "uuid-1", "name": "test"}]
        mock_client.get.return_value = {"alias": {"uuid": "uuid-1", "name": "test"}}
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = FwAliasManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(state="absent", params={"name": "test"})

        assert any("delete failed" in r.message for r in caplog.records)
