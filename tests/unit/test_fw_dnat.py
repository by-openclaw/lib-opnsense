"""Unit tests for opnsense.managers.fw_dnat.FwDnatManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.fw_dnat import FwDnatManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_dnat_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwDnatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Forward HTTPS to web server",
                "interface": "wan",
                "protocol": "tcp",
                "target": "10.6.225.10",
                "local-port": "443",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/d_nat/apply")

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when rule matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "descr": "Forward HTTPS to web server",
                "interface": "wan",
                "protocol": "tcp",
                "target": "10.6.225.10",
            },
        ]

        mgr = FwDnatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Forward HTTPS to web server",
                "interface": "wan",
                "protocol": "tcp",
                "target": "10.6.225.10",
            },
        )

        assert result.changed is False
        assert result.action == "noop"

    async def test_update_when_local_port_changes(self, mock_client: AsyncMock) -> None:
        """ensure present when local-port differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "descr": "Forward HTTPS",
                "interface": "wan",
                "target": "10.6.225.10",
                "local-port": "443",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "descr": "Forward HTTPS",
                "interface": "wan",
                "target": "10.6.225.10",
                "local-port": "443",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwDnatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Forward HTTPS",
                "interface": "wan",
                "target": "10.6.225.10",
                "local-port": "8443",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("firewall/d_nat/apply")


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_dnat_rule(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "descr": "Forward HTTPS"},
        ]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", "descr": "Forward HTTPS"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwDnatManager(mock_client)
        result = await mgr.ensure(state="absent", params={"descr": "Forward HTTPS"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("firewall/d_nat/apply")

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwDnatManager(mock_client)
        result = await mgr.ensure(state="absent", params={"descr": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestMatchKeys:
    """D-NAT uses composite match keys ['descr', 'interface', 'target']."""

    async def test_match_keys_is_composite(self) -> None:
        assert FwDnatManager._match_keys == ["descr", "interface", "target"]

    async def test_search_matches_on_composite_keys(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "descr": "Rule A", "interface": "wan", "target": "10.0.0.1"},
            {"uuid": "uuid-2", "descr": "Rule B", "interface": "wan", "target": "10.0.0.2"},
        ]

        mgr = FwDnatManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"descr": "Rule B", "interface": "wan", "target": "10.0.0.2"},
        )

        # Should match Rule B, detect no drift on existing fields
        assert result.uuid == "uuid-2"


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Rule entity suffix on d_nat endpoints."""

    async def test_search_uses_search_rule(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwDnatManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with("firewall/d_nat/searchRule", search_phrase="")

    async def test_create_uses_add_rule(self, mock_client: AsyncMock) -> None:
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwDnatManager(mock_client)
        await mgr.create(params={"descr": "test"})

        mock_client.create.assert_awaited_once_with(
            "firewall/d_nat/addRule", "rule", {"descr": "test"}
        )


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid", endpoint="firewall/d_nat/addRule"
        )

        mgr = FwDnatManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={"descr": "bad", "interface": "wan", "target": "10.6.225.10"},
            )

        assert any("create failed" in r.message for r in caplog.records)
