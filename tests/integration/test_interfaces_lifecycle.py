# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests for interface managers — VLAN + VIP CRUD.

Requires a live OPNsense 26.1+ device (test zone VM 101).

Safety boundaries:
    VLAN: CRUD with tag=1399 (unused). DO NOT touch 1310/1320/1330 (test zone infra).
    VIP:  CRUD safe — use IP alias mode with inttest- prefix, test zone IPs.

Environment variables:
    OPN_HOST, OPN_KEY, OPN_SECRET, OPN_PORT, OPN_VERIFY_SSL
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.if_vip import IfVipManager
from opnsense.managers.if_vlan import IfVlanManager

VLAN_DESCR = "inttest-vlan"
VIP_DESCR = "inttest-vip-alias"


@pytest.mark.integration
@pytest.mark.asyncio
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


@pytest.mark.integration
@pytest.mark.asyncio
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


@pytest.mark.integration
@pytest.mark.asyncio
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


@pytest.mark.integration
@pytest.mark.asyncio
class TestCleanup:
    """Final cleanup — remove any leftover test VIPs."""

    async def test_99_cleanup_vips(self, opn_client: OpnsenseClient) -> None:
        mgr = IfVipManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("descr", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
