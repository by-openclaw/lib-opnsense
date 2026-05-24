# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for DnsmasqBootManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
)
from opnsense.managers.services.dnsmasq_boot import DnsmasqBootManager


@pytest.mark.asyncio
class TestEnsure:
    async def test_creates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqBootManager(mock_client)
        r = await mgr.ensure("present", {"interface": "lan", "filename": "pxelinux.0"})
        assert r.changed is True
        assert r.action == "created"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u", "interface": "lan", "filename": "pxelinux.0"}
        ]
        mgr = DnsmasqBootManager(mock_client)
        r = await mgr.ensure("present", {"interface": "lan", "filename": "pxelinux.0"})
        assert r.action == "noop"

    async def test_check_mode(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqBootManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"interface": "lan", "filename": "pxelinux.0"},
            check_mode=True,
        )
        assert r.action == "created"
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_filename(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqBootManager(mock_client)
        with pytest.raises(FieldValidationError, match="filename"):
            await mgr.ensure("present", {"interface": "lan"})


@pytest.mark.asyncio
class TestAmbiguous:
    async def test_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "interface": "lan", "filename": "p.0"},
            {"uuid": "u2", "interface": "lan", "filename": "p.0"},
        ]
        mgr = DnsmasqBootManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure("present", {"interface": "lan", "filename": "p.0"})


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqBootManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("present", {"interface": "lan", "filename": "pxelinux.0"})
