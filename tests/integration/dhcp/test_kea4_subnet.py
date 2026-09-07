# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Kea DHCPv4 subnet manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dhcp/test_kea4_subnet.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestKea4SubnetCRUD.test_01_create
    2. Idempotent (I)   -- TestKea4SubnetCRUD.test_02_idempotent
    3. Update (U)       -- TestKea4SubnetCRUD.test_03_update
    4. Check mode (K)   -- TestKea4SubnetCRUD.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01_empty_subnet
    8. Delete (D)       -- TestKea4SubnetCRUD.test_05_delete
    9. Delete noop (Dn) -- TestKea4SubnetCRUD.test_06_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup_v4_subnets

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.dhcp.kea4_subnet import Kea4SubnetManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestKea4SubnetCRUD:
    """DHCPv4 subnet CRUD -- test subnet 10.99.0.0/24."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.0.0/24",
                "pools": "10.99.0.100-10.99.0.200",
                "description": "inttest-kea4-subnet-updated",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "subnet": "10.99.1.0/24",
                "pools": "10.99.1.100-10.99.1.200",
                "description": "inttest-kea4-checkmode",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="10.99.1.0")
        found = [row for row in rows if "10.99.1.0" in str(row.get("subnet", ""))]
        assert found == []

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        """Delete subnet."""
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"subnet": "10.99.0.0/24"},
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = Kea4SubnetManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"subnet": "10.99.0.0/24"},
        )
        assert r.changed is False
        assert r.action == "noop"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 subnet matches same CIDR."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two subnets with same CIDR via direct create."""
        # OPNsense >= 26.7 enforces "Subnet must be unique" on addSubnet, so the
        # ambiguous-match scenario cannot be staged there — skip the class.
        from opnsense.exceptions import OpnsenseValidationError as _VErr

        try:
            await self._create_dup(opn_client)
        except _VErr as exc:
            if "unique" in str(exc):
                pytest.skip(f"device enforces subnet uniqueness: {exc}")
            raise
        return

    async def _create_dup(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        r1 = await mgr.create(
            params={
                "subnet": "10.99.2.0/24",
                "pools": "10.99.2.100-10.99.2.200",
                "description": "inttest-dup-v4-a",
            }
        )
        r2 = await mgr.create(
            params={
                "subnet": "10.99.2.0/24",
                "pools": "10.99.2.100-10.99.2.200",
                "description": "inttest-dup-v4-b",
            }
        )
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = Kea4SubnetManager(opn_client)
        if len([r for r in await mgr.list("") if r.get("subnet") == "10.99.2.0/24"]) < 2:
            pytest.skip("no duplicate subnets staged (device enforces uniqueness)")
        mgr = Kea4SubnetManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "subnet": "10.99.2.0/24",
                    "description": "inttest-dup-v4-a",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate subnets by UUID."""
        mgr = Kea4SubnetManager(opn_client)
        rows = await mgr.list(search_phrase="10.99.2.0")
        for row in rows:
            if "10.99.2.0" in str(row.get("subnet", "")):
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="10.99.2.0")
        remaining = [r for r in rows if "10.99.2.0" in str(r.get("subnet", ""))]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_subnet_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required subnet -> FieldValidationError."""
        mgr = Kea4SubnetManager(opn_client)
        with pytest.raises(FieldValidationError, match="subnet"):
            await mgr.ensure("present", {"subnet": "", "description": "inttest-bad"})


class TestCleanup:
    """Remove all inttest- Kea DHCPv4 subnets."""

    async def test_cleanup_v4_subnets(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4SubnetManager(opn_client)
        rows = await mgr.list(search_phrase="10.99")
        for row in rows:
            if "10.99" in str(row.get("subnet", "")):
                await opn_client.delete("kea/dhcpv4/delSubnet", row["uuid"])
        await opn_client.reconfigure("kea/service/reconfigure", timeout=60)
