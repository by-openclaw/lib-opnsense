# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.dnsmasq_range.DnsmasqRangeManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
    OpnsenseValidationError,
)
from opnsense.managers.services.dnsmasq_range import DnsmasqRangeManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_creates_ipv4_range(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "lan",
                "subnet_mask": "255.255.255.0",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.200",
                "lease_time": "2h",
            },
        )
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid == "uuid-new"

    async def test_creates_ipv6_range(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-v6"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "lan",
                "constructor": "lan",
                "prefix_len": "64",
                "start_addr": "::1000",
                "end_addr": "::2000",
                "ra_mode": "slaac",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "interface": "lan",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.200",
                "subnet_mask": "255.255.255.0",
            }
        ]
        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "lan",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.200",
                "subnet_mask": "255.255.255.0",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_updates_when_end_addr_changes(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "interface": "lan",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.150",
                "subnet_mask": "255.255.255.0",
            }
        ]
        mock_client.get.return_value = {
            "range": {
                "interface": "lan",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.150",
                "subnet_mask": "255.255.255.0",
            }
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "lan",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.200",
                "subnet_mask": "255.255.255.0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_check_mode_does_not_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "lan",
                "subnet_mask": "255.255.255.0",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.200",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_deletes_when_exists(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-gone", "interface": "lan", "start_addr": "10.0.0.100"}
        ]
        mock_client.get.return_value = {"range": {"interface": "lan", "start_addr": "10.0.0.100"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure("absent", {"interface": "lan", "start_addr": "10.0.0.100"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_noop_when_already_gone(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqRangeManager(mock_client)
        r = await mgr.ensure("absent", {"interface": "lan", "start_addr": "10.0.0.100"})
        assert r.changed is False
        assert r.action == "noop"


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_interface(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqRangeManager(mock_client)
        with pytest.raises(FieldValidationError, match="interface"):
            await mgr.ensure(
                "present",
                {"start_addr": "10.0.0.100", "end_addr": "10.0.0.200"},
            )

    async def test_missing_start_addr(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqRangeManager(mock_client)
        with pytest.raises(FieldValidationError, match="start_addr"):
            await mgr.ensure(
                "present",
                {"interface": "lan", "end_addr": "10.0.0.200"},
            )

    async def test_invalid_ra_mode_enum(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqRangeManager(mock_client)
        with pytest.raises(FieldValidationError, match="ra_mode"):
            await mgr.ensure(
                "present",
                {
                    "interface": "lan",
                    "start_addr": "::1",
                    "ra_mode": "invalid-ra",
                },
            )


@pytest.mark.asyncio
class TestAmbiguousMatch:
    async def test_raises_when_multiple_match(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "interface": "lan", "start_addr": "10.0.0.100"},
            {"uuid": "u2", "interface": "lan", "start_addr": "10.0.0.100"},
        ]
        mgr = DnsmasqRangeManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                {
                    "interface": "lan",
                    "start_addr": "10.0.0.100",
                    "end_addr": "10.0.0.200",
                    "subnet_mask": "255.255.255.0",
                },
            )
        assert set(exc_info.value.uuids) == {"u1", "u2"}


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_create_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqRangeManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure(
                "present",
                {
                    "interface": "lan",
                    "subnet_mask": "255.255.255.0",
                    "start_addr": "10.0.0.100",
                    "end_addr": "10.0.0.200",
                },
            )

    async def test_server_validation_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError("rejected")
        mgr = DnsmasqRangeManager(mock_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {
                    "interface": "lan",
                    "subnet_mask": "255.255.255.0",
                    "start_addr": "10.0.0.100",
                    "end_addr": "10.0.0.200",
                },
            )
