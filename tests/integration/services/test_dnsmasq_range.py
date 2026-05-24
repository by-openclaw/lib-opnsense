# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Dnsmasq DHCP range manager against a live OPNsense device.

Safety boundaries:
    - Test ranges use the documentation prefix ``192.0.2.0/24``
      (RFC 5737 TEST-NET-1) on the ``lan`` (OOB) interface — never
      conflicts with real DHCP pools on production VLANs.
    - Dnsmasq is currently stopped on the test FW (per the architecture
      pivot in session memory). Creating ranges does NOT start the daemon
      — the ranges are simply config entries until dnsmasq is enabled.
    - Cleanup deletes ONLY the test ranges (matched by start_addr in the
      TEST-NET-1 block). Pre-existing ranges on the device are untouched.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.services.dnsmasq_range import DnsmasqRangeManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INTTEST_IFACE = "lan"
INTTEST_START = "192.0.2.100"
INTTEST_END_1 = "192.0.2.150"
INTTEST_END_2 = "192.0.2.200"
INTTEST_DUP_START = "192.0.2.50"
INTTEST_TESTNET_PREFIX = "192.0.2."  # used by cleanup to scope deletion


class TestDnsmasqRangeCRUD:
    async def test_01_create_ipv4(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "subnet_mask": "255.255.255.0",
                "start_addr": INTTEST_START,
                "end_addr": INTTEST_END_1,
                "lease_time": "3600",  # API wants integer seconds, not '1h'
            },
        )
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "subnet_mask": "255.255.255.0",
                "start_addr": INTTEST_START,
                "end_addr": INTTEST_END_1,
                "lease_time": "3600",  # API wants integer seconds, not '1h'
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update_end_addr(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "subnet_mask": "255.255.255.0",
                "start_addr": INTTEST_START,
                "end_addr": INTTEST_END_2,
                "lease_time": "3600",  # API wants integer seconds, not '1h'
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "subnet_mask": "255.255.255.0",
                "start_addr": "192.0.2.220",
                "end_addr": "192.0.2.240",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        rows = await mgr.list()
        assert not any(row.get("start_addr") == "192.0.2.220" for row in rows), (
            "check_mode must not create"
        )

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        r = await mgr.ensure("absent", {"interface": INTTEST_IFACE, "start_addr": INTTEST_START})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        r = await mgr.ensure("absent", {"interface": INTTEST_IFACE, "start_addr": INTTEST_START})
        assert r.changed is False
        assert r.action == "noop"


class TestAmbiguousMatch:
    """Server permits duplicate interface+start_addr; library raises."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        dup_params = {
            "interface": INTTEST_IFACE,
            "subnet_mask": "255.255.255.0",
            "start_addr": INTTEST_DUP_START,
            "end_addr": "192.0.2.80",
        }
        r1 = await mgr.create(params=dup_params)
        r2 = await mgr.create(params=dup_params)
        assert r1.uuid and r2.uuid and r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                {
                    "interface": INTTEST_IFACE,
                    "subnet_mask": "255.255.255.0",
                    "start_addr": INTTEST_DUP_START,
                    "end_addr": "192.0.2.80",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("interface") == INTTEST_IFACE and row.get("start_addr") == INTTEST_DUP_START:
                await mgr.delete(row["uuid"])


class TestFieldValidation:
    async def test_01_missing_interface(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        with pytest.raises(FieldValidationError, match="interface"):
            await mgr.ensure("present", {"subnet_mask": "255.255.255.0", "start_addr": "10.0.0.1"})

    async def test_02_invalid_ra_priority_enum(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        with pytest.raises(FieldValidationError, match="ra_priority"):
            await mgr.ensure(
                "present",
                {
                    "interface": INTTEST_IFACE,
                    "start_addr": "::1",
                    "ra_priority": "extreme",  # invalid
                },
            )


class TestCleanup:
    """Remove any TEST-NET-1 ranges left over from the suite."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqRangeManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            start = row.get("start_addr", "")
            if start.startswith(INTTEST_TESTNET_PREFIX):
                await opn_client.delete("dnsmasq/settings/delRange", row["uuid"])
        await opn_client.reconfigure("dnsmasq/service/reconfigure", timeout=15)
