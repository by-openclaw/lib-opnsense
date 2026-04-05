"""Unit tests for opnsense.managers.fw_filter.FwFilterManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.fw_filter import FwFilterManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "interface": "lan",
                "protocol": "TCP",
                "destination_port": "443",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/filter/apply")

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when rule matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "protocol": "TCP",
            },
        ]

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Allow HTTPS from DMZ", "action": "pass", "protocol": "TCP"},
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when action differs -> update + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "Block SSH", "action": "pass"},
        ]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", "description": "Block SSH", "action": "pass"},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Block SSH", "action": "block"},
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("firewall/filter/apply")


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_rule(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "Block SSH"},
        ]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", "description": "Block SSH"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "Block SSH"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("firewall/filter/apply")

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Test rule"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Rule entity suffix."""

    async def test_search_uses_search_rule(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwFilterManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with("firewall/filter/searchRule", search_phrase="")

    async def test_create_uses_add_rule(self, mock_client: AsyncMock) -> None:
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        await mgr.create(params={"description": "test", "action": "pass"})

        mock_client.create.assert_awaited_once_with(
            "firewall/filter/addRule", "rule", {"description": "test", "action": "pass"}
        )


@pytest.mark.asyncio
class TestRedactFields:
    """FwFilterManager has no sensitive fields."""

    async def test_no_redact_fields(self) -> None:
        assert len(FwFilterManager.REDACT_FIELDS) == 0


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid rule", endpoint="firewall/filter/addRule"
        )

        mgr = FwFilterManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"description": "bad"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="firewall/filter/addRule",
            validations={"rule.action": "required"},
        )

        mgr = FwFilterManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params={"description": "bad"})

        assert exc_info.value.validations == {"rule.action": "required"}
