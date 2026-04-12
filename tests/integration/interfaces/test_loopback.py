# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfLoopbackManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_loopback.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestLoopbackCRUD.test_01_create
    2. Idempotent (I)   -- TestLoopbackCRUD.test_02_idempotent
    3. Update (U)       -- N/A -- loopback has no updatable fields
    4. Check mode (K)   -- TestCheckMode.test_05_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_06..test_08)
    7. Error (E)        -- TestErrorHandling.test_09_empty_description
    8. Delete (D)       -- TestLoopbackCRUD.test_03_delete
    9. Delete noop (Dn) -- TestLoopbackCRUD.test_04_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup_loopbacks

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.interfaces.loopback import IfLoopbackManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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


class TestCheckMode:
    """Check-mode tests."""

    async def test_05_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = IfLoopbackManager(opn_client)
        result = await mgr.ensure(
            "present",
            {"description": "inttest-loopback-checkmode"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-loopback-checkmode")
        assert not any(r.get("description") == "inttest-loopback-checkmode" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate loopback data.

    Creates two loopbacks with identical description via direct create(),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {"description": "inttest-loopback-dup"}

    async def test_06_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical loopbacks via direct create (bypass ensure)."""
        mgr = IfLoopbackManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_07_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = IfLoopbackManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_08_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate loopbacks by UUID."""
        mgr = IfLoopbackManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-loopback-dup")
        dups = [r for r in rows if r.get("description") == "inttest-loopback-dup"]
        for dup in dups:
            await mgr.delete(dup["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-loopback-dup")
        remaining = [r for r in rows if r.get("description") == "inttest-loopback-dup"]
        assert remaining == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_09_empty_description_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty description (required field) -> FieldValidationError."""
        mgr = IfLoopbackManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"description": ""})


class TestCleanup:
    """Remove any leftover inttest- loopback objects."""

    async def test_cleanup_loopbacks(self, opn_client: OpnsenseClient) -> None:
        mgr = IfLoopbackManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("interfaces/loopback_settings/delItem", row["uuid"])
