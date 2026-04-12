# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfVxlanManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_vxlan.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestVxlanCRUD.test_01_create
    2. Idempotent (I)   -- TestVxlanCRUD.test_02_idempotent
    3. Update (U)       -- TestVxlanCRUD.test_03_update_vxlanremote
    4. Check mode (K)   -- TestCheckMode.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_05..test_07)
    7. Error (E)        -- TestErrorHandling.test_08_vxlanid_zero
    8. Delete (D)       -- TestVxlanCRUD.test_04_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_vxlans

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.interfaces.vxlan import IfVxlanManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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

    async def test_03_update_vxlanremote(self, opn_client: OpnsenseClient) -> None:
        """Update vxlanremote on existing VXLAN -> changed=True, action=updated."""
        mgr = IfVxlanManager(opn_client)
        # Ensure the VXLAN exists first (noop if already present from test_01)
        await mgr.ensure(
            "present",
            {
                "vxlanid": "9999",
                "vxlanlocal": "10.11.1.1",
                "vxlanremote": "10.11.2.1",
            },
        )
        # Now update the vxlanremote field
        r = await mgr.ensure(
            "present",
            {
                "vxlanid": "9999",
                "vxlanlocal": "10.11.1.1",
                "vxlanremote": "10.11.2.99",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVxlanManager(opn_client)
        r = await mgr.ensure("absent", {"vxlanid": "9999", "vxlanlocal": "10.11.1.1"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCheckMode:
    """Check-mode tests."""

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = IfVxlanManager(opn_client)
        result = await mgr.ensure(
            "present",
            {
                "vxlanid": "9998",
                "vxlanlocal": "10.11.1.1",
                "vxlanremote": "10.11.3.1",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="9998")
        assert not any(str(r.get("vxlanid", "")) == "9998" for r in rows)


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on duplicate VXLAN data.

    Creates two VXLANs with identical vxlanid+vxlanlocal via direct create(),
    then verifies ensure() raises AmbiguousMatchError.
    """

    DUP_PARAMS = {
        "vxlanid": "9997",
        "vxlanlocal": "10.11.1.1",
        "vxlanremote": "10.11.4.1",
    }

    async def test_05_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two identical VXLANs via direct create (bypass ensure)."""
        mgr = IfVxlanManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_06_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = IfVxlanManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_07_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate VXLANs by UUID."""
        mgr = IfVxlanManager(opn_client)
        rows = await mgr.list(search_phrase="9997")
        dups = [r for r in rows if str(r.get("vxlanid", "")) == "9997"]
        for dup in dups:
            await mgr.delete(dup["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="9997")
        remaining = [r for r in rows if str(r.get("vxlanid", "")) == "9997"]
        assert remaining == []


class TestErrorHandling:
    """Field validation error tests."""

    async def test_08_vxlanid_zero_raises(self, opn_client: OpnsenseClient) -> None:
        """vxlanid=0 violates int min=1 -> FieldValidationError."""
        mgr = IfVxlanManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"vxlanid": "0", "vxlanlocal": "10.11.1.1", "vxlanremote": "10.11.5.1"},
            )


class TestCleanup:
    """Remove any leftover inttest- VXLAN objects."""

    async def test_cleanup_vxlans(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVxlanManager(opn_client)
        rows = await mgr.list(search_phrase="9999")
        for row in rows:
            if str(row.get("vxlanid", "")) == "9999":
                await opn_client.delete("interfaces/vxlan_settings/delItem", row["uuid"])
        await opn_client.reconfigure("interfaces/vxlan_settings/reconfigure")
