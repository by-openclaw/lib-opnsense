# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for DdnsServiceManager and NetflowServiceManager (endpoint binding + status map)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.services.ddns_service import DdnsServiceManager
from opnsense.managers.services.netflow_service import NetflowServiceManager


@pytest.mark.asyncio
class TestDdnsService:
    async def test_status_and_reconfigure(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mock_client.post.return_value = {"status": "ok"}
        mgr = DdnsServiceManager(mock_client)
        assert await mgr.status() == "running"
        mock_client.get.assert_awaited_with("dyndns/service/status")
        assert (await mgr.ensure("reconfigured")).action == "reconfigured"
        mock_client.post.assert_awaited_once_with("dyndns/service/reconfigure", {}, timeout=60)

    async def test_restart_action(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mock_client.post.return_value = {"status": "ok"}
        r = await DdnsServiceManager(mock_client).restart()
        assert r.action == "restarted"
        mock_client.post.assert_awaited_once_with("dyndns/service/restart", {}, timeout=60)


@pytest.mark.asyncio
class TestNetflowService:
    async def test_status_maps_active_to_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "active", "collectors": "28"}
        assert await NetflowServiceManager(mock_client).status() == "running"
        mock_client.get.assert_awaited_with("diagnostics/netflow/status")
        mock_client.get.return_value = {"status": "inactive"}
        assert await NetflowServiceManager(mock_client).status() == "stopped"

    async def test_reconfigure(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "active"}
        mock_client.post.return_value = {"status": "ok"}
        r = await NetflowServiceManager(mock_client).ensure("reconfigured")
        assert r.action == "reconfigured"
        mock_client.post.assert_awaited_once_with("diagnostics/netflow/reconfigure", {}, timeout=60)

    async def test_running_is_noop_when_active(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "active"}
        assert (await NetflowServiceManager(mock_client).ensure("running")).action == "noop"
