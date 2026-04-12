# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — UbDotManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dns/test_dot.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestDotCRUD.test_01_create_disabled
    2. Idempotent (I)   -- TestDotCRUD.test_02_idempotent
    3. Update (U)       -- TestDotCRUD.test_03_update_description
    4. Check mode (K)   -- TestCheckMode.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_05..test_07)
    7. Error (E)        -- TestErrorHandling.test_08_empty_server_raises
    8. Delete (D)       -- TestDotCRUD.test_04_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_dots

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.dns.ub_dot import UbDotManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

DOT = {
    "server": "10.99.99.99",
    "port": "853",
    "type": "dot",
    "verify": "inttest.example.com",
    "enabled": "0",
    "description": "inttest-dot",
}


class TestDotCRUD:
    """CRUD lifecycle for Unbound DNS-over-TLS. Created disabled."""

    async def test_01_create_disabled(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        r = await mgr.ensure("present", DOT)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        r = await mgr.ensure("present", DOT)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update_description(self, opn_client: OpnsenseClient) -> None:
        """Update description on existing DoT entry -> changed=True, action=updated."""
        mgr = UbDotManager(opn_client)
        # Ensure the DoT entry exists first (noop if already present from test_01)
        await mgr.ensure("present", DOT)
        # Now update the description field
        r = await mgr.ensure(
            "present",
            {**DOT, "description": "updated-desc"},
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        r = await mgr.ensure("absent", {"server": "10.99.99.99", "port": "853"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCheckMode:
    """Check-mode tests."""

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = UbDotManager(opn_client)
        result = await mgr.ensure(
            "present",
            {
                "server": "10.99.99.88",
                "port": "853",
                "type": "dot",
                "verify": "inttest-checkmode.example.com",
                "enabled": "0",
                "description": "inttest-dot-checkmode",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="10.99.99.88")
        assert not any(r.get("server") == "10.99.99.88" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate DoT data.

    Creates two DoT entries with identical server+port via direct create(),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {
        "server": "10.99.99.77",
        "port": "853",
        "type": "dot",
        "verify": "inttest-dup.example.com",
        "enabled": "0",
        "description": "inttest-dot-dup",
    }

    async def test_05_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical DoT entries via direct create (bypass ensure)."""
        mgr = UbDotManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_06_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = UbDotManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_07_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate DoT entries by UUID."""
        mgr = UbDotManager(opn_client)
        rows = await mgr.list(search_phrase="10.99.99.77")
        for row in rows:
            await mgr.delete(row["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="10.99.99.77")
        assert rows == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_08_empty_server_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty server (required field) -> FieldValidationError."""
        mgr = UbDotManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"server": "", "port": "853", "type": "dot", "enabled": "0"},
            )


class TestCleanup:
    """Remove any leftover inttest- DoT entries."""

    async def test_cleanup_dots(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        rows = await mgr.list(search_phrase="10.99.99.99")
        for row in rows:
            await opn_client.delete("unbound/settings/delDot", row["uuid"])
