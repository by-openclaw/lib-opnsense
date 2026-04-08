# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — extra interface managers on live OPNsense device.

Tests Loopback, Neighbor (static ARP), and VXLAN — safe CRUD on any device.
Bridge, GIF, GRE, LAGG skipped — require physical interfaces or specific topology.

All test objects use ``inttest-`` prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.if_loopback import IfLoopbackManager
from opnsense.managers.if_neighbor import IfNeighborManager
from opnsense.managers.if_vxlan import IfVxlanManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Loopback CRUD
# =============================================================================


class TestLoopbackCRUD:
    """Loopback interface CRUD — safest interface type, no dependencies."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IfLoopbackManager(opn_client)
        r = await mgr.ensure("present", {"description": "inttest-loopback"})
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = IfLoopbackManager(opn_client)
        r = await mgr.ensure("present", {"description": "inttest-loopback"})
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IfLoopbackManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-loopback"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_04_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = IfLoopbackManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-loopback"})
        assert r.changed is False
        assert r.action == "noop"


# =============================================================================
# 2. Neighbor (static ARP) CRUD
# =============================================================================


class TestNeighborCRUD:
    """Static ARP entry CRUD — safe, does not affect routing."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IfNeighborManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "ipaddress": "10.11.1.250",
                "etheraddr": "00:11:22:33:44:55",
                "descr": "inttest-neighbor",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = IfNeighborManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "ipaddress": "10.11.1.250",
                "etheraddr": "00:11:22:33:44:55",
                "descr": "inttest-neighbor",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = IfNeighborManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "ipaddress": "10.11.1.250",
                "etheraddr": "00:11:22:33:44:55",
                "descr": "inttest-neighbor-updated",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IfNeighborManager(opn_client)
        r = await mgr.ensure(
            "absent", {"ipaddress": "10.11.1.250", "etheraddr": "00:11:22:33:44:55"}
        )
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 3. VXLAN CRUD
# =============================================================================


class TestVxlanCRUD:
    """VXLAN tunnel CRUD — safe with test IPs."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVxlanManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "vxlanid": "9999",
                "vxlanlocal": "10.11.1.1",
                "vxlanremote": "10.11.2.1",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVxlanManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "vxlanid": "9999",
                "vxlanlocal": "10.11.1.1",
                "vxlanremote": "10.11.2.1",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVxlanManager(opn_client)
        r = await mgr.ensure("absent", {"vxlanid": "9999", "vxlanlocal": "10.11.1.1"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 4. Cleanup
# =============================================================================


class TestCleanup:
    """Remove any leftover inttest- objects."""

    async def test_cleanup_loopbacks(self, opn_client: OpnsenseClient) -> None:
        mgr = IfLoopbackManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("interfaces/loopback_settings/delItem", row["uuid"])

    async def test_cleanup_neighbors(self, opn_client: OpnsenseClient) -> None:
        mgr = IfNeighborManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("interfaces/neighbor_settings/delItem", row["uuid"])

    async def test_cleanup_vxlans(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVxlanManager(opn_client)
        rows = await mgr.list(search_phrase="9999")
        for row in rows:
            if str(row.get("vxlanid", "")) == "9999":
                await opn_client.delete("interfaces/vxlan_settings/delItem", row["uuid"])
        await opn_client.reconfigure("interfaces/vxlan_settings/reconfigure")
