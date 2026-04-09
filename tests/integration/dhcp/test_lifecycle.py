# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Kea DHCP managers on live OPNsense device.

Kea DHCPv4: full CRUD tested (subnet, reservation, peer).
Kea DHCPv6: API available but requires interface configured in Kea general
settings. Subnet creation fails if no DHCPv6 interface is enabled. Unit
tested only until Kea DHCPv6 is configured on the test device.

All test objects use inttest- prefix and test subnets (10.99.0.0/24, fd00:99::/64).
Reservations require parent subnet UUID — create subnet first, then reservation.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.kea4_peer import Kea4PeerManager
from opnsense.managers.kea4_reservation import Kea4ReservationManager
from opnsense.managers.kea4_subnet import Kea4SubnetManager
from opnsense.managers.kea6_subnet import Kea6SubnetManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Kea DHCPv4 Subnet CRUD
# =============================================================================


class TestKea4SubnetCRUD:
    """DHCPv4 subnet CRUD — test subnet 10.99.0.0/24."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet-updated",
            },
        )
        assert r.changed is True
        assert r.action == "updated"


# =============================================================================
# 2. Kea DHCPv4 Reservation CRUD (needs parent subnet)
# =============================================================================


class TestKea4ReservationCRUD:
    """DHCPv4 reservation CRUD — requires parent subnet UUID."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        # Find parent subnet UUID
        subnet_mgr = Kea4SubnetManager(opn_client)
        rows = await subnet_mgr.list(search_phrase="10.99.0.0")
        parent = [r for r in rows if "10.99.0.0" in str(r.get("subnet", ""))]
        assert len(parent) >= 1, "Parent subnet must exist"
        subnet_uuid = parent[0]["uuid"]

        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": subnet_uuid,
                "ip_address": "10.99.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "inttest-host",
                "description": "inttest-kea4-reserv",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "ip_address": "10.99.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "inttest-host",
                "description": "inttest-kea4-reserv",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"ip_address": "10.99.0.50", "hw_address": "00:11:22:33:44:55"},
        )
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 3. Kea DHCPv4 Peer CRUD
# =============================================================================


class TestKea4PeerCRUD:
    """DHCPv4 HA peer CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-peer",
                "role": "primary",
                "url": "http://10.99.0.1:8000/",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-peer"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 4. Kea DHCPv6 Subnet CRUD
# =============================================================================


class TestKea6SubnetCRUD:
    """DHCPv6 subnet CRUD — requires interface field (lan)."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "fd00:99::/64",
                "interface": "lan",
                "description": "inttest-kea6-subnet",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "fd00:99::/64",
                "interface": "lan",
                "description": "inttest-kea6-subnet",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure("absent", {"subnet": "fd00:99::/64"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 5. Cleanup
# =============================================================================


class TestCleanup:
    """Remove all inttest- Kea objects (reservations first, then subnets)."""

    async def test_cleanup_v4_reservations(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4ReservationManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "") or row.get("hostname", "")):
                await opn_client.delete("kea/dhcpv4/delReservation", row["uuid"])

    async def test_cleanup_v4_subnets(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        rows = await mgr.list(search_phrase="10.99")
        for row in rows:
            if "10.99" in str(row.get("subnet", "")):
                await opn_client.delete("kea/dhcpv4/delSubnet", row["uuid"])

    async def test_cleanup_v4_peers(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4PeerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("kea/dhcpv4/delPeer", row["uuid"])

    async def test_cleanup_v6_subnets(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        rows = await mgr.list(search_phrase="fd00:99")
        for row in rows:
            if "fd00:99" in str(row.get("subnet", "")):
                await opn_client.delete("kea/dhcpv6/delSubnet", row["uuid"])
        await opn_client.reconfigure("kea/service/reconfigure", timeout=60)
