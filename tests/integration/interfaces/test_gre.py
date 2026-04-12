# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfGreManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_gre.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestGreCRUD.test_01_create
    2. Idempotent (I)   -- TestGreCRUD.test_02_idempotent
    3. Update (U)       -- TestGreCRUD.test_03_update_descr
    4. Check mode (K)   -- TestCheckMode.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_05..test_07)
    7. Error (E)        -- TestErrorHandling.test_08_missing_required
    8. Delete (D)       -- TestGreCRUD.test_04_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_gres

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.interfaces.gre import IfGreManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestGreCRUD:
    """GRE tunnel CRUD — safe with test IPs (10.99.x.x range)."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IfGreManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "tunnel-local-addr": "10.99.2.1",
                "tunnel-remote-addr": "10.99.2.2",
                "local-addr": "10.11.1.1",
                "remote-addr": "10.11.1.3",
                "descr": "inttest-gre",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = IfGreManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "tunnel-local-addr": "10.99.2.1",
                "tunnel-remote-addr": "10.99.2.2",
                "local-addr": "10.11.1.1",
                "remote-addr": "10.11.1.3",
                "descr": "inttest-gre",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update_descr(self, opn_client: OpnsenseClient) -> None:
        """Update descr on existing GRE tunnel -> changed=True, action=updated."""
        mgr = IfGreManager(opn_client)
        # Ensure the GRE tunnel exists first (noop if already present from test_01)
        await mgr.ensure(
            "present",
            {
                "tunnel-local-addr": "10.99.2.1",
                "tunnel-remote-addr": "10.99.2.2",
                "local-addr": "10.11.1.1",
                "remote-addr": "10.11.1.3",
                "descr": "inttest-gre",
            },
        )
        # Now update the descr field
        r = await mgr.ensure(
            "present",
            {
                "tunnel-local-addr": "10.99.2.1",
                "tunnel-remote-addr": "10.99.2.2",
                "local-addr": "10.11.1.1",
                "remote-addr": "10.11.1.3",
                "descr": "inttest-gre-updated",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IfGreManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"tunnel-local-addr": "10.99.2.1", "tunnel-remote-addr": "10.99.2.2"},
        )
        assert r.changed is True
        assert r.action == "deleted"


class TestCheckMode:
    """Check-mode tests."""

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = IfGreManager(opn_client)
        result = await mgr.ensure(
            "present",
            {
                "tunnel-local-addr": "10.99.3.1",
                "tunnel-remote-addr": "10.99.3.2",
                "local-addr": "10.11.1.1",
                "remote-addr": "10.11.1.3",
                "descr": "inttest-gre-checkmode",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-gre-checkmode")
        assert not any(r.get("descr") == "inttest-gre-checkmode" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate GRE tunnel data.

    Creates two GRE tunnels with identical match keys via direct create(),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {
        "tunnel-local-addr": "10.99.4.1",
        "tunnel-remote-addr": "10.99.4.2",
        "local-addr": "10.11.1.1",
        "remote-addr": "10.11.1.3",
        "descr": "inttest-gre-dup",
    }

    async def test_05_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical GRE tunnels via direct create (bypass ensure)."""
        mgr = IfGreManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_06_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = IfGreManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_07_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate GRE tunnels by UUID."""
        mgr = IfGreManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-gre-dup")
        dups = [r for r in rows if r.get("descr") == "inttest-gre-dup"]
        for dup in dups:
            await mgr.delete(dup["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-gre-dup")
        remaining = [r for r in rows if r.get("descr") == "inttest-gre-dup"]
        assert remaining == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_08_missing_required_raises(self, opn_client: OpnsenseClient) -> None:
        """Missing required tunnel-local-addr -> FieldValidationError."""
        mgr = IfGreManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {
                    "tunnel-local-addr": "",
                    "tunnel-remote-addr": "10.99.5.2",
                    "descr": "inttest-gre-bad",
                },
            )


class TestCleanup:
    """Remove any leftover inttest- GRE tunnel objects."""

    async def test_cleanup_gres(self, opn_client: OpnsenseClient) -> None:
        mgr = IfGreManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("interfaces/gre_settings/delItem", row["uuid"])
        await opn_client.reconfigure("interfaces/gre_settings/reconfigure")
