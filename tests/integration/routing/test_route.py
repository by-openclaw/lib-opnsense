# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — RtRouteManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/routing/test_route.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestRouteCRUD.test_01_create_disabled_route
    2. Idempotent (I)   -- TestRouteCRUD.test_02_idempotent
    3. Update (U)       -- TestRouteCRUD.test_03_update_description
    4. Check mode (K)   -- TestRouteCRUD.test_04_check_mode_delete
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_05)
    7. Error (E)        -- N/A -- no FieldValidationError test
    8. Delete (D)       -- TestRouteCRUD.test_05_delete
    9. Delete noop (Dn) -- TestRouteCRUD.test_06_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup_routes

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.routing.route import RtRouteManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 route matches composite keys."""

    DUP_PARAMS = {
        "network": "10.99.99.0/24",
        "gateway": "Null4",
        "descr": "inttest-dup-route",
        "disabled": "1",
    }

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two routes with same network+gateway via direct create."""
        mgr = RtRouteManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = RtRouteManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_03_ensure_absent_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = RtRouteManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={"network": "10.99.99.0/24", "gateway": "Null4"},
            )

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """ensure(uuid=) bypasses _find_existing — works on ambiguous pair."""
        mgr = RtRouteManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-route")
        dups = [r for r in rows if r.get("descr") == "inttest-dup-route"]
        assert len(dups) == 2
        result = await mgr.ensure(state="present", uuid=dups[0]["uuid"], params=self.DUP_PARAMS)
        assert result.action == "noop"

    async def test_05_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate routes by UUID."""
        mgr = RtRouteManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-route")
        for r in rows:
            if r.get("descr") == "inttest-dup-route":
                await mgr.delete(r["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-route")
        remaining = [r for r in rows if r.get("descr") == "inttest-dup-route"]
        assert remaining == []


class TestCleanup:
    """Remove any leftover inttest- routes. NEVER touch gateways."""

    async def test_cleanup_routes(self, opn_client: OpnsenseClient) -> None:
        mgr = RtRouteManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("routes/routes/delRoute", row["uuid"])
        await opn_client.reconfigure("routes/routes/reconfigure")
