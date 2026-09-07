# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Kea DHCPv6 subnet manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dhcp/test_kea6_subnet.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestKea6SubnetCRUD.test_01_create
    2. Idempotent (I)   -- TestKea6SubnetCRUD.test_02_idempotent
    3. Update (U)       -- TestKea6SubnetCRUD.test_04_update_description
    4. Check mode (K)   -- TestKea6SubnetCRUD.test_03_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- no ambiguous match test
    7. Error (E)        -- TestFieldValidation.test_01_empty_subnet
    8. Delete (D)       -- TestKea6SubnetCRUD.test_05_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_v6_subnets

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.dhcp.kea6_subnet import Kea6SubnetManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# The device must have the test interface selected in Kea DHCPv6 *general* settings, otherwise
# addSubnet is refused ("Interface is not selected in the general settings"). A stock/seeded
# FW has none selected — skip the CRUD suite there instead of failing on a precondition.
@pytest.fixture(autouse=True)
async def _kea6_interface_precondition(opn_client):
    from opnsense.managers.dhcp.kea6_settings import Kea6SettingsManager

    general = await Kea6SettingsManager(opn_client).get()
    raw = general.get("interfaces", {})
    selected = (
        [k for k, v in raw.items() if isinstance(v, dict) and v.get("selected")]
        if isinstance(raw, dict)
        else []
    )
    if not selected:
        pytest.skip(
            "Kea DHCPv6: no interface selected in general settings — subnet CRUD cannot be staged"
        )


class TestKea6SubnetCRUD:
    """DHCPv6 subnet CRUD -- requires interface field (lan)."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "fd00:99::/64",
                "interface": "lan",
                "description": "inttest-kea6-subnet",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "fd00:99::/64",
                "interface": "lan",
                "description": "inttest-kea6-subnet",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "fd00:98::/64",
                "interface": "lan",
                "description": "inttest-kea6-checkmode",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="fd00:98")
        found = [row for row in rows if "fd00:98" in str(row.get("subnet", ""))]
        assert found == []

    async def test_04_update_description(self, opn_client: OpnsenseClient) -> None:
        """Update description on existing subnet -> changed=True, action=updated."""
        mgr = Kea6SubnetManager(opn_client)
        # Ensure the subnet exists first (noop if already present from test_01)
        await mgr.ensure(
            "present",
            {
                "subnet": "fd00:99::/64",
                "interface": "lan",
                "description": "inttest-kea6-subnet",
            },
        )
        # Now update the description field
        r = await mgr.ensure(
            "present",
            {
                "subnet": "fd00:99::/64",
                "interface": "lan",
                "description": "updated-desc",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        r = await mgr.ensure("absent", {"subnet": "fd00:99::/64"})
        assert r.changed is True
        assert r.action == "deleted"


# Ambiguous match: N/A — OPNsense enforces subnet uniqueness at API level.
# Direct create() with duplicate subnet returns: "Subnet must be unique."


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_subnet_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required subnet -> FieldValidationError."""
        mgr = Kea6SubnetManager(opn_client)
        with pytest.raises(FieldValidationError, match="subnet"):
            await mgr.ensure(
                "present",
                {"subnet": "", "interface": "lan", "description": "inttest-bad"},
            )


class TestCleanup:
    """Remove all inttest- Kea DHCPv6 subnets."""

    async def test_cleanup_v6_subnets(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea6SubnetManager(opn_client)
        rows = await mgr.list(search_phrase="fd00:99")
        for row in rows:
            if "fd00:99" in str(row.get("subnet", "")):
                await opn_client.delete("kea/dhcpv6/delSubnet", row["uuid"])
        await opn_client.reconfigure("kea/service/reconfigure", timeout=60)
