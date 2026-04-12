# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — UbHostOverrideManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dns/test_host_override.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestHostOverrideCRUD.test_01_create
    2. Idempotent (I)   -- TestHostOverrideCRUD.test_02_idempotent
    3. Update (U)       -- TestHostOverrideCRUD.test_03_update
    4. Check mode (K)   -- TestHostOverrideCRUD.test_04_check_mode_delete
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_05)
    7. Error (E)        -- N/A -- no FieldValidationError tests
    8. Delete (D)       -- TestHostOverrideCRUD.test_05_delete
    9. Delete noop (Dn) -- TestHostOverrideCRUD.test_06_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup_host_overrides

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.dns.ub_host_override import UbHostOverrideManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

HOST_OVERRIDE = {
    "hostname": "inttest-web",
    "domain": "lab.test",
    "server": "10.11.2.10",
    "rr": "A",
    "enabled": "1",
    "description": "inttest-host-override",
}


class TestHostOverrideCRUD:
    """CRUD lifecycle for Unbound host overrides."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure("present", HOST_OVERRIDE)
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure("present", HOST_OVERRIDE)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        updated = {**HOST_OVERRIDE, "description": "inttest-host-override-updated"}
        r = await mgr.ensure("present", updated)
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"hostname": "inttest-web", "domain": "lab.test", "server": "10.11.2.10"},
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "deleted"
        # Still exists after check_mode
        r2 = await mgr.ensure("present", HOST_OVERRIDE)
        assert r2.action in ("noop", "updated")

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"hostname": "inttest-web", "domain": "lab.test", "server": "10.11.2.10"},
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"hostname": "inttest-web", "domain": "lab.test", "server": "10.11.2.10"},
        )
        assert r.changed is False
        assert r.action == "noop"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 host override matches composite keys."""

    DUP_PARAMS = {
        "hostname": "inttest-dup",
        "domain": "lab.test",
        "server": "10.11.2.99",
        "rr": "A",
        "description": "inttest-dup-host-override",
    }

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two host overrides with same hostname+domain+server via direct create."""
        mgr = UbHostOverrideManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = UbHostOverrideManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_03_ensure_absent_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = UbHostOverrideManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "hostname": "inttest-dup",
                    "domain": "lab.test",
                    "server": "10.11.2.99",
                },
            )

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """ensure(uuid=) bypasses _find_existing — works on ambiguous pair."""
        mgr = UbHostOverrideManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup")
        dups = [r for r in rows if r.get("hostname") == "inttest-dup"]
        assert len(dups) == 2
        result = await mgr.ensure(state="present", uuid=dups[0]["uuid"], params=self.DUP_PARAMS)
        assert result.action == "noop"

    async def test_05_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate host overrides by UUID."""
        mgr = UbHostOverrideManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup")
        for r in rows:
            if r.get("hostname") == "inttest-dup":
                await mgr.delete(r["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup")
        remaining = [r for r in rows if r.get("hostname") == "inttest-dup"]
        assert remaining == []


class TestCleanup:
    """Remove any leftover inttest- host overrides."""

    async def test_cleanup_host_overrides(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("hostname", "")):
                await opn_client.delete("unbound/settings/delHostOverride", row["uuid"])
        await opn_client.reconfigure("unbound/service/reconfigure", timeout=60)
