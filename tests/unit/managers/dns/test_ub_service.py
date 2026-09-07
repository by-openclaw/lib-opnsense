# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.dns.ub_service.UbServiceManager.

Most behaviour is inherited from ``BaseServiceManager`` and exercised in
``tests/unit/core/test_base_service.py``. These tests verify endpoint binding,
``_apply_timeout`` propagation and the ``disabled`` status semantics.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.dns.ub_service import UbServiceManager


@pytest.mark.asyncio
class TestEndpointWiring:
    async def test_status_hits_unbound_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "disabled"}
        mgr = UbServiceManager(mock_client)
        assert await mgr.status() == "disabled"
        mock_client.get.assert_awaited_once_with("unbound/service/status")

    async def test_start_when_stopped(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "stopped"},
            {"status": "stopped"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"response": "OK"}
        mgr = UbServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is True
        assert result.action == "started"
        mock_client.post.assert_awaited_once_with("unbound/service/start", {}, timeout=60)

    async def test_noop_when_already_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mgr = UbServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_stopped_is_noop_while_disabled(self, mock_client: AsyncMock) -> None:
        """'disabled' (general.enabled=0) counts as stopped."""
        mock_client.get.return_value = {"status": "disabled"}
        mgr = UbServiceManager(mock_client)
        result = await mgr.ensure("stopped")
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_reconfigure_uses_apply_timeout(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [{"status": "running"}, {"status": "running"}]
        mock_client.post.return_value = {"status": "ok"}
        mgr = UbServiceManager(mock_client)
        result = await mgr.ensure("reconfigured")
        assert result.action == "reconfigured"
        mock_client.post.assert_awaited_once_with("unbound/service/reconfigure", {}, timeout=60)


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_start_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "stopped"}
        mock_client.post.side_effect = OpnsenseServerError("daemon refused")
        mgr = UbServiceManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("running")


@pytest.mark.asyncio
class TestInvalidState:
    async def test_raises_on_unsupported_state(self, mock_client: AsyncMock) -> None:
        mgr = UbServiceManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("present")
