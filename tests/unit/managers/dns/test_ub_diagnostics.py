# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.ub_diagnostics.UbDiagnosticsManager.

NOT a BaseManager — 3 read-only methods: get_stats, get_dnsbl, list_dnsbl.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.dns.ub_diagnostics import UbDiagnosticsManager


@pytest.fixture
def diag_client() -> AsyncMock:
    """Create a mocked OpnsenseClient for diagnostics tests."""
    client = AsyncMock(spec=OpnsenseClient)
    client._base_url = "https://opnsense.example.com"
    return client


@pytest.mark.asyncio
class TestGetStats:
    """Tests for get_stats()."""

    async def test_get_stats_returns_dict(self, diag_client: AsyncMock) -> None:
        diag_client.get.return_value = {
            "thread0": {"queries": "1234"},
            "cache": {"rrset": "500"},
        }

        mgr = UbDiagnosticsManager(diag_client)
        result = await mgr.get_stats()

        assert isinstance(result, dict)
        assert "thread0" in result
        diag_client.get.assert_awaited_once_with("unbound/diagnostics/stats")

    async def test_get_stats_error_reraises(self, diag_client: AsyncMock) -> None:
        diag_client.get.side_effect = RuntimeError("connection refused")

        mgr = UbDiagnosticsManager(diag_client)
        with pytest.raises(RuntimeError, match="connection refused"):
            await mgr.get_stats()


@pytest.mark.asyncio
class TestGetDnsbl:
    """Tests for get_dnsbl()."""

    async def test_get_dnsbl_returns_blocklist_dict(self, diag_client: AsyncMock) -> None:
        diag_client.get.return_value = {
            "blocklist": {
                "enabled": "1",
                "type": "custom",
                "lists": ["list1", "list2"],
            },
        }

        mgr = UbDiagnosticsManager(diag_client)
        result = await mgr.get_dnsbl()

        assert isinstance(result, dict)
        assert result["enabled"] == "1"
        diag_client.get.assert_awaited_once_with("unbound/settings/getDnsbl")

    async def test_get_dnsbl_fallback_when_no_blocklist_key(self, diag_client: AsyncMock) -> None:
        """When response has no 'blocklist' key, return full body."""
        diag_client.get.return_value = {"enabled": "0", "type": "none"}

        mgr = UbDiagnosticsManager(diag_client)
        result = await mgr.get_dnsbl()

        assert result["enabled"] == "0"

    async def test_get_dnsbl_error_reraises(self, diag_client: AsyncMock) -> None:
        diag_client.get.side_effect = RuntimeError("timeout")

        mgr = UbDiagnosticsManager(diag_client)
        with pytest.raises(RuntimeError, match="timeout"):
            await mgr.get_dnsbl()


@pytest.mark.asyncio
class TestListDnsbl:
    """Tests for list_dnsbl()."""

    async def test_list_dnsbl_returns_list(self, diag_client: AsyncMock) -> None:
        diag_client.search.return_value = [
            {"uuid": "bl-1", "type": "ads"},
            {"uuid": "bl-2", "type": "malware"},
        ]

        mgr = UbDiagnosticsManager(diag_client)
        result = await mgr.list_dnsbl()

        assert isinstance(result, list)
        assert len(result) == 2
        diag_client.search.assert_awaited_once_with("unbound/settings/searchDnsbl")
