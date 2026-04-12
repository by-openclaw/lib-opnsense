# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Kea DHCPv4 reservation manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dhcp/test_kea4_reservation.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestKea4ReservationCRUD.test_01_create
    2. Idempotent (I)   -- TestKea4ReservationCRUD.test_02_idempotent
    3. Update (U)       -- TestKea4ReservationCRUD.test_04_update_hostname
    4. Check mode (K)   -- TestKea4ReservationCRUD.test_03_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- no ambiguous match test
    7. Error (E)        -- TestFieldValidation.test_01_bad_ip_rejected
    8. Delete (D)       -- TestKea4ReservationCRUD.test_05_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup (reservations + parent subnet)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.dhcp.kea4_reservation import Kea4ReservationManager
from opnsense.managers.dhcp.kea4_subnet import Kea4SubnetManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestKea4ReservationCRUD:
    """DHCPv4 reservation CRUD -- requires parent subnet UUID."""

    async def test_00_setup_parent_subnet(self, opn_client: OpnsenseClient) -> None:
        """Create parent subnet 10.99.0.0/24 for reservation tests."""
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet",
            },
        )
        assert r.action in ("created", "noop")

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        # Find parent subnet UUID
        subnet_mgr = Kea4SubnetManager(opn_client)
        rows = await subnet_mgr.list(search_phrase="10.99.0.0")
        parent = [r for r in rows if "10.99.0.0" in str(r.get("subnet", ""))]
        assert len(parent) >= 1, "Parent subnet must exist"
        subnet_uuid = parent[0]["uuid"]

        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": subnet_uuid,
                "ip_address": "10.99.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "inttest-host",
                "description": "inttest-kea4-reserv",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "ip_address": "10.99.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "inttest-host",
                "description": "inttest-kea4-reserv",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        subnet_mgr = Kea4SubnetManager(opn_client)
        rows = await subnet_mgr.list(search_phrase="10.99.0.0")
        parent = [r for r in rows if "10.99.0.0" in str(r.get("subnet", ""))]
        assert len(parent) >= 1
        subnet_uuid = parent[0]["uuid"]

        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": subnet_uuid,
                "ip_address": "10.99.0.60",
                "hw_address": "00:11:22:33:44:66",
                "hostname": "inttest-checkmode",
                "description": "inttest-kea4-reserv-cm",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        all_rows = await mgr.list(search_phrase="inttest-checkmode")
        found = [row for row in all_rows if "inttest-checkmode" in str(row.get("hostname", ""))]
        assert found == []

    async def test_04_update_hostname(self, opn_client: OpnsenseClient) -> None:
        """Update hostname on existing reservation -> changed=True, action=updated."""
        mgr = Kea4ReservationManager(opn_client)
        # Ensure the reservation exists first (noop if already present from test_01)
        await mgr.ensure(
            "present",
            {
                "ip_address": "10.99.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "inttest-host",
                "description": "inttest-kea4-reserv",
            },
        )
        # Now update the hostname field
        r = await mgr.ensure(
            "present",
            {
                "ip_address": "10.99.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "updated-host",
                "description": "inttest-kea4-reserv",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4ReservationManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"ip_address": "10.99.0.50", "hw_address": "00:11:22:33:44:55"},
        )
        assert r.changed is True
        assert r.action == "deleted"


# Ambiguous match: N/A — Kea4 reservation requires parent subnet UUID in create().
# The API validates ip_address is within the subnet range. Duplicate detection
# is hard to test because create() needs the subnet UUID which isn't a match key.
# Reservations are matched by ip_address + hw_address (composite key).


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_bad_ip_rejected(self, opn_client: OpnsenseClient) -> None:
        """Bad IP address -> FieldValidationError."""
        mgr = Kea4ReservationManager(opn_client)
        with pytest.raises(FieldValidationError, match="ip_address"):
            await mgr.ensure(
                "present",
                {
                    "ip_address": "999.999.999.999",
                    "hw_address": "00:11:22:33:44:55",
                    "hostname": "inttest-bad-ip",
                },
            )


class TestCleanup:
    """Remove all inttest- reservations first, then parent subnet."""

    async def test_cleanup_reservations(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4ReservationManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "") or row.get("hostname", "")):
                await opn_client.delete("kea/dhcpv4/delReservation", row["uuid"])

    async def test_cleanup_parent_subnet(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        rows = await mgr.list(search_phrase="10.99")
        for row in rows:
            if "10.99" in str(row.get("subnet", "")):
                await opn_client.delete("kea/dhcpv4/delSubnet", row["uuid"])
        await opn_client.reconfigure("kea/service/reconfigure", timeout=60)
