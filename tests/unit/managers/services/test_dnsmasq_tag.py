# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for DnsmasqTagManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
)
from opnsense.managers.services.dnsmasq_tag import DnsmasqTagManager


@pytest.mark.asyncio
class TestEnsure:
    async def test_creates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqTagManager(mock_client)
        r = await mgr.ensure("present", {"tag": "iot-clients"})
        assert r.changed is True
        assert r.action == "created"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "u", "tag": "iot-clients"}]
        mgr = DnsmasqTagManager(mock_client)
        r = await mgr.ensure("present", {"tag": "iot-clients"})
        assert r.action == "noop"

    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "u", "tag": "iot-clients"}]
        mock_client.get.return_value = {"tag": {"tag": "iot-clients"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqTagManager(mock_client)
        r = await mgr.ensure("absent", {"tag": "iot-clients"})
        assert r.action == "deleted"


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_tag(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqTagManager(mock_client)
        with pytest.raises(FieldValidationError, match="tag"):
            await mgr.ensure("present", {})


@pytest.mark.asyncio
class TestAmbiguous:
    async def test_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "tag": "dup"},
            {"uuid": "u2", "tag": "dup"},
        ]
        mgr = DnsmasqTagManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure("present", {"tag": "dup"})


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqTagManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("present", {"tag": "iot"})
