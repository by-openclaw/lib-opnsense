# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.crowdsec.service.CrowdSecServiceManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.crowdsec.service import CrowdSecServiceManager


@pytest.mark.asyncio
class TestStatus:
    async def test_status_endpoint(self, mock_client: AsyncMock) -> None:
        """status() hits crowdsec/service/status."""
        mock_client.get.return_value = {"status": "running"}
        mgr = CrowdSecServiceManager(mock_client)
        assert await mgr.status() == "running"
        mock_client.get.assert_awaited_once_with("crowdsec/service/status")


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_already_running(self, mock_client: AsyncMock) -> None:
        """ensure('running') on a running service -> noop, no POST."""
        mock_client.get.return_value = {"status": "running"}
        mgr = CrowdSecServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_starts_when_stopped(self, mock_client: AsyncMock) -> None:
        """ensure('running') on a stopped service starts it."""
        # ensure() reads status before the action and again afterwards; the base
        # class also re-reads inside _action, so supply a stable sequence.
        mock_client.get.side_effect = [
            {"status": "stopped"},
            {"status": "running"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"status": "ok"}
        mgr = CrowdSecServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is True
        assert result.action == "started"

    async def test_check_mode_does_not_post(self, mock_client: AsyncMock) -> None:
        """check_mode reports the transition without performing it."""
        mock_client.get.return_value = {"status": "stopped"}
        mgr = CrowdSecServiceManager(mock_client)
        result = await mgr.ensure("running", check_mode=True)
        assert result.changed is True
        mock_client.post.assert_not_awaited()
