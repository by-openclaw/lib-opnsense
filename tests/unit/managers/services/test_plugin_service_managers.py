# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for the plugin service controllers (chrony, lldpd, qemu-guest-agent,
dnscrypt-proxy) — endpoint binding, ``_apply_timeout`` propagation, disabled semantics.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.dns.dnscrypt_service import DnscryptProxyServiceManager
from opnsense.managers.services.chrony_service import ChronyServiceManager
from opnsense.managers.services.lldpd_service import LldpdServiceManager
from opnsense.managers.services.qemuguestagent_service import QemuGuestAgentServiceManager

CASES = [
    (ChronyServiceManager, "chrony/service"),
    (LldpdServiceManager, "lldpd/service"),
    (QemuGuestAgentServiceManager, "qemuguestagent/service"),
    (DnscryptProxyServiceManager, "dnscryptproxy/service"),
]
IDS = ["chrony", "lldpd", "qemuguestagent", "dnscrypt"]


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,endpoint", CASES, ids=IDS)
class TestPluginService:
    async def test_status_hits_endpoint(self, mock_client: AsyncMock, cls, endpoint):
        mock_client.get.return_value = {"status": "disabled"}
        assert await cls(mock_client).status() == "disabled"
        mock_client.get.assert_awaited_once_with(f"{endpoint}/status")

    async def test_start_when_stopped(self, mock_client: AsyncMock, cls, endpoint):
        mock_client.get.side_effect = [
            {"status": "stopped"},
            {"status": "stopped"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"response": "OK"}
        result = await cls(mock_client).ensure("running")
        assert result.changed is True and result.action == "started"
        mock_client.post.assert_awaited_once_with(f"{endpoint}/start", {}, timeout=60)

    async def test_noop_when_running(self, mock_client: AsyncMock, cls, endpoint):
        mock_client.get.return_value = {"status": "running"}
        result = await cls(mock_client).ensure("running")
        assert result.changed is False and result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_disabled_counts_as_stopped(self, mock_client: AsyncMock, cls, endpoint):
        mock_client.get.return_value = {"status": "disabled"}
        assert (await cls(mock_client).ensure("stopped")).action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_reconfigure_uses_apply_timeout(self, mock_client: AsyncMock, cls, endpoint):
        mock_client.get.side_effect = [{"status": "running"}, {"status": "running"}]
        mock_client.post.return_value = {"status": "ok"}
        assert (await cls(mock_client).ensure("reconfigured")).action == "reconfigured"
        mock_client.post.assert_awaited_once_with(f"{endpoint}/reconfigure", {}, timeout=60)

    async def test_start_failure_propagates(self, mock_client: AsyncMock, cls, endpoint):
        mock_client.get.return_value = {"status": "stopped"}
        mock_client.post.side_effect = OpnsenseServerError("daemon refused")
        with pytest.raises(OpnsenseServerError):
            await cls(mock_client).ensure("running")

    async def test_invalid_state(self, mock_client: AsyncMock, cls, endpoint):
        with pytest.raises(ValueError):
            await cls(mock_client).ensure("present")
