# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfVlanManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_vlan.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestVlanCRUD.test_01_create_vlan
    2. Idempotent (I)   -- TestVlanCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestVlanCRUD.test_05_update_descr
    4. Check mode (K)   -- TestCheckModeAndValidation.test_08_check_mode
    5. Read/list (R)    -- TestVlanCRUD.test_04_list_contains_test_vlan
    6. Ambiguous (A)    -- N/A -- API enforces tag+if uniqueness
    7. Error (E)        -- TestCheckModeAndValidation.test_09_tag_zero
    8. Delete (D)       -- TestVlanCRUD.test_06_delete_vlan
    9. Delete noop (Dn) -- TestVlanCRUD.test_07_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_vlans

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.interfaces.vlan import IfVlanManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

VLAN_DESCR = "inttest-vlan"


class TestVlanCRUD:
    """VLAN CRUD lifecycle. Uses tag=1399 (unused). DO NOT touch 1310/1320/1330."""

    async def test_01_create_vlan(self, opn_client: OpnsenseClient) -> None:
        """Create a test VLAN on vtnet0 (LAN trunk), or noop if leftover."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"if": "vtnet0", "tag": "1399", "descr": VLAN_DESCR},
        )
        assert result.action in ("created", "updated", "noop")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"if": "vtnet0", "tag": "1399", "descr": VLAN_DESCR},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_get_schema(self, opn_client: OpnsenseClient) -> None:
        """Schema returns VLAN field definitions."""
        mgr = IfVlanManager(opn_client)
        schema = await mgr.get_schema()
        assert "tag" in schema
        assert "descr" in schema

    async def test_04_list_contains_test_vlan(self, opn_client: OpnsenseClient) -> None:
        """Search confirms test VLAN exists."""
        mgr = IfVlanManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        assert any(r.get("descr") == VLAN_DESCR for r in rows)

    async def test_05_update_descr(self, opn_client: OpnsenseClient) -> None:
        """Update description -> changed (descr is not a match key anymore)."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"if": "vtnet0", "tag": "1399", "descr": "inttest-vlan-updated"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_05b_restore_descr(self, opn_client: OpnsenseClient) -> None:
        """Restore original description for delete test."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"if": "vtnet0", "tag": "1399", "descr": VLAN_DESCR},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_06_delete_vlan(self, opn_client: OpnsenseClient) -> None:
        """Delete the test VLAN."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"tag": "1399", "if": "vtnet0"},
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_07_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"tag": "1399", "if": "vtnet0"},
        )
        assert result.changed is False
        assert result.action == "noop"


class TestCheckModeAndValidation:
    """Check-mode and field validation tests."""

    async def test_08_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = IfVlanManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"if": "vtnet0", "tag": "1398", "descr": "inttest-vlan-checkmode"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-vlan-checkmode")
        assert not any(r.get("descr") == "inttest-vlan-checkmode" for r in rows)

    async def test_09_field_validation_tag_zero(self, opn_client: OpnsenseClient) -> None:
        """tag=0 violates int min=1 -> FieldValidationError."""
        mgr = IfVlanManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                state="present",
                params={"if": "vtnet0", "tag": "0", "descr": "inttest-vlan-badtag"},
            )


class TestCleanup:
    """Final cleanup — remove any leftover test VLANs."""

    async def test_99_cleanup_vlans(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVlanManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("descr", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
