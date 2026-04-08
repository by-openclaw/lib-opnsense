"""Unit tests for opnsense.managers.fw_source_nat.FwSourceNatManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.fw_source_nat import FwSourceNatManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_snat_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwSourceNatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Masquerade DMZ to WAN",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/source_nat/apply", timeout=None)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Masquerade DMZ to WAN",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
            },
        ]

        mgr = FwSourceNatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Masquerade DMZ to WAN",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
            },
        )

        assert result.changed is False
        assert result.action == "noop"

    async def test_update_when_target_changes(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "SNAT rule",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "description": "SNAT rule",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwSourceNatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "SNAT rule",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "10.6.224.1",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("firewall/source_nat/apply", timeout=None)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_snat_rule(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "SNAT rule"},
        ]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", "description": "SNAT rule"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwSourceNatManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "SNAT rule"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("firewall/source_nat/apply", timeout=None)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwSourceNatManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Rule entity suffix on source_nat endpoints."""

    async def test_search_uses_search_rule(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwSourceNatManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with(
            "firewall/source_nat/searchRule", search_phrase=""
        )


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid", endpoint="firewall/source_nat/addRule"
        )

        mgr = FwSourceNatManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={"description": "bad", "interface": "wan", "source_net": "10.6.225.0/24"},
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="firewall/source_nat/addRule",
            validations={"rule.interface": "required"},
        )

        mgr = FwSourceNatManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(
                state="present",
                params={"description": "bad", "interface": "wan", "source_net": "10.6.225.0/24"},
            )

        assert exc_info.value.validations == {"rule.interface": "required"}
