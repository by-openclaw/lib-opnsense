# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — UbAclManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dns/test_acl.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestAclCRUD.test_01_create
    2. Idempotent (I)   -- TestAclCRUD.test_02_idempotent
    3. Update (U)       -- TestAclCRUD.test_03_update
    4. Check mode (K)   -- TestCheckMode.test_05_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_06..test_08)
    7. Error (E)        -- TestErrorHandling.test_09_empty_name_raises
    8. Delete (D)       -- TestAclCRUD.test_04_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_acls

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.dns.ub_acl import UbAclManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

ACL = {
    "name": "inttest-acl-testzone",
    "action": "allow",
    "networks": "10.11.0.0/16",
    "enabled": "1",
    "description": "inttest-acl",
}


class TestAclCRUD:
    """CRUD lifecycle for Unbound access control lists."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        r = await mgr.ensure("present", ACL)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        r = await mgr.ensure("present", ACL)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        updated = {**ACL, "description": "inttest-acl-updated"}
        r = await mgr.ensure("present", updated)
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-acl-testzone"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCheckMode:
    """Check-mode tests."""

    async def test_05_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = UbAclManager(opn_client)
        result = await mgr.ensure(
            "present",
            {
                "name": "inttest-acl-checkmode",
                "action": "allow",
                "networks": "10.11.0.0/16",
                "enabled": "1",
                "description": "inttest-acl-checkmode",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-acl-checkmode")
        assert not any(r.get("name") == "inttest-acl-checkmode" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate ACL data.

    Creates two ACLs with identical name via direct create(),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {
        "name": "inttest-acl-dup",
        "action": "allow",
        "networks": "10.11.0.0/16",
        "enabled": "1",
        "description": "inttest-acl-dup",
    }

    async def test_06_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical ACLs via direct create (bypass ensure)."""
        mgr = UbAclManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_07_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = UbAclManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_08_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate ACLs by UUID."""
        mgr = UbAclManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-acl-dup")
        dups = [r for r in rows if r.get("name") == "inttest-acl-dup"]
        for dup in dups:
            await mgr.delete(dup["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-acl-dup")
        remaining = [r for r in rows if r.get("name") == "inttest-acl-dup"]
        assert remaining == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_09_empty_name_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty name (required field) -> FieldValidationError."""
        mgr = UbAclManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"name": "", "action": "allow", "networks": "10.11.0.0/16"},
            )


class TestCleanup:
    """Remove any leftover inttest- ACLs."""

    async def test_cleanup_acls(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("unbound/settings/delAcl", row["uuid"])
