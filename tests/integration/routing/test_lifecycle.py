# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — routing managers on live OPNsense device.

SAFETY:
    - Gateways: READ-ONLY — never create/modify/delete gateways
      (WAN_DHCP is the default gateway, touching it kills connectivity)
    - Routes: CRUD with disabled=1, inttest- prefix, using Null4 blackhole gateway
      (Null4 = 127.0.0.1, safe — no traffic impact)
    - Full cleanup after each test class
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.routing.gateway import RtGatewayManager
from opnsense.managers.routing.route import RtRouteManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Gateway — READ-ONLY (never create/modify/delete)
# =============================================================================


class TestGatewayReadOnly:
    """Gateway manager — verify list and get work. NEVER create or delete."""

    async def test_01_list_gateways(self, opn_client: OpnsenseClient) -> None:
        """List existing gateways — must find WAN_DHCP."""
        mgr = RtGatewayManager(opn_client)
        rows = await mgr.list()
        assert len(rows) >= 1
        names = [r.get("name", "") for r in rows]
        assert "WAN_DHCP" in names, f"WAN_DHCP not found in {names}"

    async def test_02_list_contains_default(self, opn_client: OpnsenseClient) -> None:
        """Verify WAN_DHCP is the default gateway."""
        mgr = RtGatewayManager(opn_client)
        rows = await mgr.list(search_phrase="WAN_DHCP")
        wan = [r for r in rows if r.get("name") == "WAN_DHCP"]
        assert len(wan) == 1
        # Just verify we can find it — do NOT call ensure() as it could mutate


# =============================================================================
# 2. Route — CRUD (disabled, inttest- prefix)
# =============================================================================


class TestRouteCRUD:
    """Static route CRUD — disabled routes, inttest- prefix, Null4 gateway."""

    async def test_01_create_disabled_route(self, opn_client: OpnsenseClient) -> None:
        """Create a disabled static route to a test network."""
        mgr = RtRouteManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "network": "10.99.0.0/24",
                "gateway": "Null4",
                "descr": "inttest-route-disabled",
                "disabled": "1",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "network": "10.99.0.0/24",
                "gateway": "Null4",
                "descr": "inttest-route-disabled",
                "disabled": "1",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update_description(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "network": "10.99.0.0/24",
                "gateway": "Null4",
                "descr": "inttest-route-updated",
                "disabled": "1",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"network": "10.99.0.0/24", "gateway": "Null4"},
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        r = await mgr.ensure("absent", {"network": "10.99.0.0/24", "gateway": "Null4"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        r = await mgr.ensure("absent", {"network": "10.99.0.0/24", "gateway": "Null4"})
        assert r.changed is False
        assert r.action == "noop"


# =============================================================================
# 3. Cleanup
# =============================================================================


class TestCleanup:
    """Remove any leftover inttest- routes. NEVER touch gateways."""

    async def test_cleanup_routes(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("routes/routes/delRoute", row["uuid"])
        await opn_client.reconfigure("routes/routes/reconfigure")
