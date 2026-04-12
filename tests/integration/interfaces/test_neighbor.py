# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfNeighborManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_neighbor.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestNeighborCRUD.test_01_create
    2. Idempotent (I)   -- TestNeighborCRUD.test_02_idempotent
    3. Update (U)       -- TestNeighborCRUD.test_03_update
    4. Check mode (K)   -- TestCheckMode.test_05_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_06..test_08)
    7. Error (E)        -- TestErrorHandling.test_09_empty_ipaddress
    8. Delete (D)       -- TestNeighborCRUD.test_04_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_neighbors

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.interfaces.neighbor import IfNeighborManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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


class TestCheckMode:
    """Check-mode tests."""

    async def test_05_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = IfNeighborManager(opn_client)
        result = await mgr.ensure(
            "present",
            {
                "ipaddress": "10.11.1.251",
                "etheraddr": "00:11:22:33:44:66",
                "descr": "inttest-neighbor-checkmode",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-neighbor-checkmode")
        assert not any(r.get("descr") == "inttest-neighbor-checkmode" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate neighbor data.

    Creates two identical neighbors via direct create() (bypassing ensure),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {
        "ipaddress": "10.11.1.252",
        "etheraddr": "00:11:22:33:44:77",
        "descr": "inttest-neighbor-dup",
    }

    async def test_06_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical neighbors via direct create (bypass ensure)."""
        mgr = IfNeighborManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_07_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = IfNeighborManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_08_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate neighbors by UUID."""
        mgr = IfNeighborManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-neighbor-dup")
        dups = [r for r in rows if r.get("descr") == "inttest-neighbor-dup"]
        for dup in dups:
            await mgr.delete(dup["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-neighbor-dup")
        remaining = [r for r in rows if r.get("descr") == "inttest-neighbor-dup"]
        assert remaining == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_09_empty_ipaddress_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty ipaddress (required field) -> FieldValidationError."""
        mgr = IfNeighborManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"ipaddress": "", "etheraddr": "00:11:22:33:44:88", "descr": "inttest-bad"},
            )


class TestCleanup:
    """Remove any leftover inttest- neighbor objects."""

    async def test_cleanup_neighbors(self, opn_client: OpnsenseClient) -> None:
        mgr = IfNeighborManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("interfaces/neighbor_settings/delItem", row["uuid"])
