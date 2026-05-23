# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.radvd_service.RadvdServiceManager.

Most behavior is inherited from ``BaseServiceManager`` and exercised in
``tests/unit/core/test_base_service.py``. These tests verify the concrete
manager's endpoint binding + ``_apply_timeout`` propagation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.services.radvd_service import RadvdServiceManager


@pytest.mark.asyncio
class TestEndpointWiring:
    """Verify the radvd service controller binds to the right endpoints."""

    async def test_status_hits_radvd_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mgr = RadvdServiceManager(mock_client)
        result = await mgr.status()
        assert result == "running"
        mock_client.get.assert_awaited_once_with("radvd/service/status")

    async def test_start_when_stopped(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "stopped"},
            {"status": "stopped"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"response": "OK"}
        mgr = RadvdServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is True
        assert result.action == "started"
        mock_client.post.assert_awaited_once_with("radvd/service/start", {}, timeout=30)

    async def test_noop_when_already_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mgr = RadvdServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_reconfigure_uses_apply_timeout(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "running"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"status": "ok"}
        mgr = RadvdServiceManager(mock_client)
        await mgr.ensure("reconfigured")
        mock_client.post.assert_awaited_once_with("radvd/service/reconfigure", {}, timeout=30)


@pytest.mark.asyncio
class TestErrorPropagation:
    """ADR §10.2 cases 1+2 — failures are logged and re-raised unchanged."""

    async def test_start_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "stopped"}
        mock_client.post.side_effect = OpnsenseServerError("daemon crashed")
        mgr = RadvdServiceManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("running")


@pytest.mark.asyncio
class TestInvalidState:
    """ensure() rejects bad state values inherited from BaseServiceManager."""

    async def test_raises_on_unsupported_state(self, mock_client: AsyncMock) -> None:
        mgr = RadvdServiceManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("present")
        mock_client.get.assert_not_awaited()
