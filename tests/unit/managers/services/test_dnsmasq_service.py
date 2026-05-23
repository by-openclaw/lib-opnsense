# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.dnsmasq_service.DnsmasqServiceManager.

Most behavior is inherited from ``BaseServiceManager`` and exercised in
``tests/unit/core/test_base_service.py``. These tests verify endpoint binding
and ``_apply_timeout`` propagation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.services.dnsmasq_service import DnsmasqServiceManager


@pytest.mark.asyncio
class TestEndpointWiring:
    async def test_status_hits_dnsmasq_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mgr = DnsmasqServiceManager(mock_client)
        assert await mgr.status() == "running"
        mock_client.get.assert_awaited_once_with("dnsmasq/service/status")

    async def test_stop_when_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "running"},
            {"status": "running"},
            {"status": "stopped"},
        ]
        mock_client.post.return_value = {"response": "OK"}
        mgr = DnsmasqServiceManager(mock_client)
        result = await mgr.ensure("stopped")
        assert result.changed is True
        assert result.action == "stopped"
        mock_client.post.assert_awaited_once_with("dnsmasq/service/stop", {}, timeout=30)

    async def test_noop_when_already_stopped(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "stopped"}
        mgr = DnsmasqServiceManager(mock_client)
        result = await mgr.ensure("stopped")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_reconfigure_uses_apply_timeout(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "running"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"status": "ok"}
        mgr = DnsmasqServiceManager(mock_client)
        await mgr.ensure("reconfigured")
        mock_client.post.assert_awaited_once_with("dnsmasq/service/reconfigure", {}, timeout=30)


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_stop_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mock_client.post.side_effect = OpnsenseServerError("daemon refused")
        mgr = DnsmasqServiceManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("stopped")


@pytest.mark.asyncio
class TestInvalidState:
    async def test_raises_on_unsupported_state(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqServiceManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("present")
