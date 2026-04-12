# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — UbForwardManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dns/test_forward.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestForwardCRUD.test_01_create
    2. Idempotent (I)   -- TestForwardCRUD.test_02_idempotent
    3. Update (U)       -- TestForwardCRUD.test_03_update_description
    4. Check mode (K)   -- TestCheckMode.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_05..test_07)
    7. Error (E)        -- TestErrorHandling.test_08_empty_domain_raises
    8. Delete (D)       -- TestForwardCRUD.test_04_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_forwards

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.dns.ub_forward import UbForwardManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

FORWARD = {
    "domain": "inttest.test",
    "server": "10.11.1.53",
    "type": "forward",
    "enabled": "1",
    "description": "inttest-forward",
}


class TestForwardCRUD:
    """CRUD lifecycle for Unbound DNS forwarding."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        r = await mgr.ensure("present", FORWARD)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        r = await mgr.ensure("present", FORWARD)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update_description(self, opn_client: OpnsenseClient) -> None:
        """Update description on existing forward -> changed=True, action=updated."""
        mgr = UbForwardManager(opn_client)
        # Ensure the forward exists first (noop if already present from test_01)
        await mgr.ensure("present", FORWARD)
        # Now update the description field
        r = await mgr.ensure(
            "present",
            {**FORWARD, "description": "updated-desc"},
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        r = await mgr.ensure("absent", {"domain": "inttest.test", "server": "10.11.1.53"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCheckMode:
    """Check-mode tests."""

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = UbForwardManager(opn_client)
        result = await mgr.ensure(
            "present",
            {
                "domain": "inttest-checkmode.test",
                "server": "10.11.1.53",
                "type": "forward",
                "enabled": "1",
                "description": "inttest-forward-checkmode",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-checkmode")
        assert not any(r.get("domain") == "inttest-checkmode.test" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate forward data.

    Creates two forwards with identical domain+server via direct create(),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {
        "domain": "inttest-dup.test",
        "server": "10.11.1.53",
        "type": "forward",
        "enabled": "1",
        "description": "inttest-forward-dup",
    }

    async def test_05_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical forwards via direct create (bypass ensure)."""
        mgr = UbForwardManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_06_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = UbForwardManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_07_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate forwards by UUID."""
        mgr = UbForwardManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup")
        dups = [r for r in rows if r.get("domain") == "inttest-dup.test"]
        for dup in dups:
            await mgr.delete(dup["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup")
        remaining = [r for r in rows if r.get("domain") == "inttest-dup.test"]
        assert remaining == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_08_empty_domain_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty domain (required field) -> FieldValidationError."""
        mgr = UbForwardManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"domain": "", "server": "10.11.1.53", "type": "forward"},
            )


class TestCleanup:
    """Remove any leftover inttest- DNS forwards."""

    async def test_cleanup_forwards(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("domain", "")):
                await opn_client.delete("unbound/settings/delForward", row["uuid"])
