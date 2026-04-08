"""Unit tests for opnsense.managers.ub_acl.UbAclManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.ub_acl import UbAclManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_acl(self, mock_client: AsyncMock) -> None:
        """ensure present when ACL does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "lan-access",
                "action": "allow",
                "networks": "10.0.0.0/8",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when ACL matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "lan-access",
                "action": "allow",
                "networks": "10.0.0.0/8",
            },
        ]

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "lan-access",
                "action": "allow",
                "networks": "10.0.0.0/8",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when action differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "lan-access",
                "action": "allow",
                "networks": "10.0.0.0/8",
            },
        ]
        mock_client.get.return_value = {
            "acl": {
                "uuid": "uuid-existing",
                "name": "lan-access",
                "action": "allow",
                "networks": "10.0.0.0/8",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "lan-access",
                "action": "deny",
                "networks": "10.0.0.0/8",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_acl(self, mock_client: AsyncMock) -> None:
        """ensure absent when ACL exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "lan-access"},
        ]
        mock_client.get.return_value = {
            "acl": {"uuid": "uuid-existing", "name": "lan-access"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "lan-access"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when ACL does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "lan-access", "action": "allow"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "lan-access"},
        ]
        mock_client.get.return_value = {
            "acl": {"uuid": "uuid-1", "name": "lan-access"},
        }

        mgr = UbAclManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "lan-access"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid acl", endpoint="unbound/settings/addAcl"
        )

        mgr = UbAclManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"name": "bad-acl"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "lan-access"},
        ]
        mock_client.get.return_value = {
            "acl": {"uuid": "uuid-1", "name": "lan-access"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="unbound/settings/delAcl"
        )

        mgr = UbAclManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"name": "lan-access"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_name_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = UbAclManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"action": "allow"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_action_enum_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = UbAclManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "test", "action": "permit"})
        mock_client.create.assert_not_awaited()
