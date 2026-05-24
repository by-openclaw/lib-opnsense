# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for DnsmasqOptionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
)
from opnsense.managers.services.dnsmasq_option import DnsmasqOptionManager


@pytest.mark.asyncio
class TestEnsure:
    async def test_creates_v4(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "u"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqOptionManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"interface": "lan", "option": "3", "value": "10.0.0.1"},
        )
        assert r.action == "created"

    async def test_creates_v6(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "u"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqOptionManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"interface": "lan", "option6": "23", "value": "fd00::1"},
        )
        assert r.action == "created"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "u",
                "interface": "lan",
                "option": "3",
                "option6": "",
                "value": "10.0.0.1",
                "type": "set",
            }
        ]
        mgr = DnsmasqOptionManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "lan",
                "option": "3",
                "option6": "",
                "value": "10.0.0.1",
                "type": "set",
            },
        )
        assert r.action == "noop"


@pytest.mark.asyncio
class TestValidation:
    async def test_invalid_type_enum(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqOptionManager(mock_client)
        with pytest.raises(FieldValidationError, match="type"):
            await mgr.ensure("present", {"option": "3", "type": "invalid", "value": "x"})

    async def test_invalid_force_bool(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqOptionManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"option": "3", "force": "not-a-bool", "value": "x"},
            )


@pytest.mark.asyncio
class TestAmbiguous:
    async def test_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "interface": "lan", "option": "3", "option6": ""},
            {"uuid": "u2", "interface": "lan", "option": "3", "option6": ""},
        ]
        mgr = DnsmasqOptionManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                "present",
                {"interface": "lan", "option": "3", "option6": "", "value": "x"},
            )


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqOptionManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("present", {"interface": "lan", "option": "3", "value": "x"})
