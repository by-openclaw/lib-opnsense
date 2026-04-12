# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall interface group CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_group.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestGroupCRUD.test_01_create_group
    2. Idempotent (I)   -- TestGroupCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestGroupCRUD.test_03_update_description
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- API enforces ifname uniqueness
    7. Error (E)        -- TestErrorHandling.test_01_empty_ifname_rejected
    8. Delete (D)       -- TestGroupCRUD.test_04_delete_group
    9. Delete noop (Dn) -- TestGroupCRUD.test_05_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_groups

Naming convention:
    All test objects use prefix 'inttest_' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.firewall.group import FwGroupManager

GROUP_IFNAME = "inttest_grp"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestGroupCRUD:
    """CRUD lifecycle for firewall interface groups. No apply needed."""

    async def test_01_create_group(self, opn_client: OpnsenseClient) -> None:
        """Create an interface group."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": GROUP_IFNAME, "members": "lan", "descr": "Integration test group"},
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": GROUP_IFNAME, "members": "lan", "descr": "Integration test group"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_description(self, opn_client: OpnsenseClient) -> None:
        """Update description -> changed."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": GROUP_IFNAME, "members": "lan", "descr": "Updated test group"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_group(self, opn_client: OpnsenseClient) -> None:
        """Delete interface group."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"ifname": GROUP_IFNAME})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_05_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"ifname": GROUP_IFNAME})
        assert result.changed is False
        assert result.action == "noop"


class TestCheckMode:
    """Check mode -- ensure(present, check_mode=True) reports changed but does not create."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but group NOT actually created."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": "inttest_chk", "members": "lan", "descr": "Should not exist"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify the group was NOT created on the device
        rows = await mgr.list(search_phrase="inttest_chk")
        assert not any(r.get("ifname") == "inttest_chk" for r in rows)


# N/A -- OPNsense API enforces ifname uniqueness at the server level.
# Interface group names must be unique; the API rejects duplicates.
# AmbiguousMatchError can never occur for firewall interface groups.


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError."""

    async def test_01_empty_ifname_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required ifname caught client-side -- FieldValidationError."""
        mgr = FwGroupManager(opn_client)
        with pytest.raises(FieldValidationError, match="ifname"):
            await mgr.ensure(
                state="present",
                params={"ifname": "", "members": "lan", "descr": "Should fail"},
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test interface groups."""

    async def test_99_cleanup_groups(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest_ interface groups."""
        mgr = FwGroupManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("ifname", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
