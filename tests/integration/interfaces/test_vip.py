# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfVipManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_vip.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestVipCrud.test_01_create_vip
    2. Idempotent (I)   -- TestVipCrud.test_02_idempotent_noop
    3. Update (U)       -- TestVipCrud.test_04_update_descr
    4. Check mode (K)   -- TestVipCrud.test_05_check_mode_delete
    5. Read/list (R)    -- TestVipCrud.test_03_get_created_vip
    6. Ambiguous (A)    -- N/A -- no ambiguous match test
    7. Error (E)        -- TestErrorHandling.test_01 + test_02
    8. Delete (D)       -- TestVipCrud.test_06_delete_vip
    9. Delete noop (Dn) -- TestVipCrud.test_07_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_vips

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.interfaces.vip import IfVipManager
from opnsense.managers.interfaces.vlan import IfVlanManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

VIP_DESCR = "inttest-vip-alias"


class TestVipCrud:
    """VIP CRUD lifecycle — safe IP alias on LAN."""

    async def test_01_create_vip(self, opn_client: OpnsenseClient) -> None:
        """Create an IP alias VIP on LAN."""
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "interface": "lan",
                "mode": "ipalias",
                "address": "10.11.1.200/32",
                "network": "10.11.1.200/32",
                "descr": VIP_DESCR,
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "interface": "lan",
                "mode": "ipalias",
                "address": "10.11.1.200/32",
                "network": "10.11.1.200/32",
                "descr": VIP_DESCR,
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_get_created_vip(self, opn_client: OpnsenseClient) -> None:
        """Get the created VIP by searching."""
        mgr = IfVipManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        assert any(r.get("descr") == VIP_DESCR for r in rows)

    async def test_04_update_descr(self, opn_client: OpnsenseClient) -> None:
        """Update VIP description -> changed.

        Note: ``address`` is a composite match key and cannot be used for
        drift/update tests.  We update ``descr`` instead.
        """
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "interface": "lan",
                "mode": "ipalias",
                "address": "10.11.1.200/32",
                "network": "10.11.1.200/32",
                "descr": VIP_DESCR + "-updated",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_05_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        """check_mode delete -> reports changed but VIP still exists."""
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "address": "10.11.1.200/32",
                "interface": "lan",
                "mode": "ipalias",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"

        # VIP should still exist
        rows = await mgr.list(search_phrase="inttest")
        assert any(r.get("descr", "").startswith(VIP_DESCR) for r in rows)

    async def test_06_delete_vip(self, opn_client: OpnsenseClient) -> None:
        """Delete the VIP."""
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "address": "10.11.1.200/32",
                "interface": "lan",
                "mode": "ipalias",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_07_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "address": "10.11.1.200/32",
                "interface": "lan",
                "mode": "ipalias",
            },
        )
        assert result.changed is False
        assert result.action == "noop"


class TestErrorHandling:
    """Error handling tests against live device."""

    async def test_01_invalid_state(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVlanManager(opn_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"descr": "test"})

    async def test_02_check_mode_no_side_effects(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> no resource created on device."""
        mgr = IfVipManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "interface": "lan",
                "mode": "ipalias",
                "address": "10.11.1.250/32",
                "network": "10.11.1.250/32",
                "descr": "inttest-should-not-exist",
            },
            check_mode=True,
        )
        assert result.changed is True

        rows = await mgr.list(search_phrase="inttest-should-not-exist")
        assert not any(r.get("descr") == "inttest-should-not-exist" for r in rows)


# NOTE: VLAN duplicates are rejected by OPNsense API (tag must be unique per parent).
# No TestAmbiguousMatch needed — same behavior as auth domain.


class TestCleanup:
    """Final cleanup — remove any leftover test VIPs."""

    async def test_99_cleanup_vips(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVipManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("descr", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
