"""Unit tests for opnsense.managers.auth_group.AuthGroupManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.auth_group import AuthGroupManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_group(self, mock_client: AsyncMock) -> None:
        """ensure present when group does not exist -> create."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-grp"

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "grp-admins", "description": "Admin group"},
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-grp"
        mock_client.create.assert_awaited_once()

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when group exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-grp", "name": "grp-admins", "description": "Admin group"},
        ]

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "grp-admins", "description": "Admin group"},
        )

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-grp"

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when group description differs -> update."""
        mock_client.search.return_value = [
            {"uuid": "uuid-grp", "name": "grp-admins", "description": "Old desc"},
        ]
        mock_client.get.return_value = {
            "group": {"uuid": "uuid-grp", "name": "grp-admins", "description": "Old desc"},
        }
        mock_client.update.return_value = {"result": "saved"}

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "grp-admins", "description": "New desc"},
        )

        assert result.changed is True
        assert result.action == "updated"


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_group(self, mock_client: AsyncMock) -> None:
        """ensure absent when group exists -> delete."""
        mock_client.search.return_value = [
            {"uuid": "uuid-grp", "name": "grp-test"},
        ]
        mock_client.get.return_value = {
            "group": {"uuid": "uuid-grp", "name": "grp-test"},
        }
        mock_client.delete.return_value = {"result": "deleted"}

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "grp-test"},
        )

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when group does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "nonexistent"},
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "grp-test"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()

    async def test_check_mode_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-grp", "name": "grp-test"},
        ]

        mgr = AuthGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "grp-test"},
            check_mode=True,
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on AuthGroupManager."""

    async def test_no_redact_fields(self) -> None:
        """AuthGroupManager has no sensitive fields to redact."""
        assert set() == AuthGroupManager.REDACT_FIELDS
