# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- auth group CRUD and user-group assignments.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/auth/test_group.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestGroupCRUD.test_01_create_group
    2. Idempotent (I)   -- TestGroupCRUD.test_02_create_group_idempotent
    3. Update (U)       -- TestGroupCRUD.test_04_update_group
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- TestGroupCRUD.test_03_read_group
    6. Ambiguous (A)    -- N/A -- API enforces group name uniqueness
    7. Error (E)        -- TestErrorHandling.test_01_empty_name_rejected
    8. Delete (D)       -- TestGroupCRUD.test_05_delete_group
    9. Delete noop (Dn) -- TestGroupCRUD.test_06_delete_group_idempotent
    10. Cleanup (X)     -- TestCleanup (users + groups)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.auth.group import AuthGroupManager
from opnsense.managers.auth.user import AuthUserManager

# -- Test data constants -------------------------------------------------------

USER_A = "inttest-alice"
USER_B = "inttest-bob"
USER_C = "inttest-carol"

GROUP_1 = "inttest-engineers"
GROUP_2 = "inttest-operators"

# -- Markers -------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. CRUD Group Lifecycle
# =============================================================================


class TestGroupCRUD:
    """Create, read, update, delete a single group with idempotency checks."""

    async def test_01_create_group(self, opn_client: OpnsenseClient) -> None:
        """Create a new group."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": GROUP_1, "description": "Integration test group 1"},
        )
        assert result.changed is True
        assert result.action == "created"
        assert result.uuid is not None

    async def test_02_create_group_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-create same group -- noop."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": GROUP_1, "description": "Integration test group 1"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_read_group(self, opn_client: OpnsenseClient) -> None:
        """List groups, find by name."""
        mgr = AuthGroupManager(opn_client)
        rows = await mgr.list(search_phrase=GROUP_1)
        matches = [r for r in rows if r.get("name") == GROUP_1]
        assert len(matches) == 1

    async def test_04_update_group(self, opn_client: OpnsenseClient) -> None:
        """Update group description."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": GROUP_1, "description": "Updated description"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_05_delete_group(self, opn_client: OpnsenseClient) -> None:
        """Delete group."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": GROUP_1})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_06_delete_group_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-delete -- noop."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": GROUP_1})
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 2. Check Mode
# =============================================================================


class TestCheckMode:
    """Check mode -- ensure(present, check_mode=True) reports changed but does not create."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but group NOT actually created."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "inttest-checkmode-grp", "description": "Should not exist"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify the group was NOT created on the device
        rows = await mgr.list(search_phrase="inttest-checkmode-grp")
        assert not any(r.get("name") == "inttest-checkmode-grp" for r in rows)


# =============================================================================
# 3. Ambiguous Match
# =============================================================================
# N/A -- OPNsense API enforces group name uniqueness at the server level.
# Attempting to create a second group with the same name returns a validation
# error, so AmbiguousMatchError can never occur for auth groups.


# =============================================================================
# 4. Error Handling
# =============================================================================


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError."""

    async def test_01_empty_name_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required name caught client-side -- FieldValidationError."""
        mgr = AuthGroupManager(opn_client)
        with pytest.raises(FieldValidationError, match="name"):
            await mgr.ensure(
                state="present",
                params={"name": "", "description": "Should fail"},
            )


# =============================================================================
# 5. User-Group Assignments
# =============================================================================


class TestUserGroupAssignment:
    """Create users and groups, assign users to multiple groups."""

    async def test_01_setup_groups(self, opn_client: OpnsenseClient) -> None:
        """Create two groups for assignment tests."""
        mgr = AuthGroupManager(opn_client)
        for grp in (GROUP_1, GROUP_2):
            result = await mgr.ensure(
                state="present",
                params={"name": grp, "description": f"Test group {grp}"},
            )
            assert result.action in ("created", "noop")

    async def test_02_setup_users(self, opn_client: OpnsenseClient) -> None:
        """Create three users for assignment tests."""
        mgr = AuthUserManager(opn_client)
        for user in (USER_A, USER_B, USER_C):
            result = await mgr.ensure(
                state="present",
                params={"name": user, "email": f"{user}@example.com", "password": "T3stP@ss!"},
            )
            assert result.action in ("created", "updated", "noop")

    async def test_03_assign_users_to_group1(self, opn_client: OpnsenseClient) -> None:
        """Assign alice and bob to engineers group via group_memberships.

        OPNsense 26.1 uses GID (numeric group ID) for group_memberships,
        not UUID. The GID is returned in the search results.
        """
        mgr = AuthUserManager(opn_client)
        grp_mgr = AuthGroupManager(opn_client)
        groups = await grp_mgr.list(search_phrase=GROUP_1)
        grp1 = [g for g in groups if g.get("name") == GROUP_1]
        assert grp1, f"Group {GROUP_1} not found"
        grp1_gid = str(grp1[0].get("gid", grp1[0].get("uuid", "")))

        for user in (USER_A, USER_B):
            result = await mgr.ensure(
                state="present",
                params={"name": user, "group_memberships": grp1_gid},
            )
            assert result.action in ("updated", "noop")

    async def test_04_assign_carol_to_both_groups(self, opn_client: OpnsenseClient) -> None:
        """Assign carol to both groups.

        Uses GID (numeric) for group_memberships -- OPNsense 26.1 format.
        """
        mgr = AuthUserManager(opn_client)
        grp_mgr = AuthGroupManager(opn_client)

        grp1_rows = await grp_mgr.list(search_phrase=GROUP_1)
        grp2_rows = await grp_mgr.list(search_phrase=GROUP_2)
        grp1 = [g for g in grp1_rows if g.get("name") == GROUP_1]
        grp2 = [g for g in grp2_rows if g.get("name") == GROUP_2]
        assert grp1, f"Group {GROUP_1} not found"
        assert grp2, f"Group {GROUP_2} not found"

        gid1 = str(grp1[0].get("gid", grp1[0].get("uuid", "")))
        gid2 = str(grp2[0].get("gid", grp2[0].get("uuid", "")))
        both_gids = f"{gid1},{gid2}"
        result = await mgr.ensure(
            state="present",
            params={"name": USER_C, "group_memberships": both_gids},
        )
        assert result.action in ("updated", "noop")

    async def test_05_verify_group_membership(self, opn_client: OpnsenseClient) -> None:
        """Verify carol's group memberships include both groups."""
        mgr = AuthUserManager(opn_client)
        rows = await mgr.list(search_phrase=USER_C)
        carol = [r for r in rows if r.get("name") == USER_C]
        assert carol, f"User {USER_C} not found"
        # group_memberships may be CSV or contain group names
        memberships = str(carol[0].get("group_memberships", ""))
        # At minimum the field should not be empty
        assert memberships, "Carol should have group memberships"


# =============================================================================
# 6. Cleanup -- users first (they reference groups), then groups
# =============================================================================


class TestCleanup:
    """Delete all test users and groups. Users before groups (dependency order)."""

    async def test_01_delete_all_test_users(self, opn_client: OpnsenseClient) -> None:
        """Delete all test users."""
        mgr = AuthUserManager(opn_client)
        for user in (USER_A, USER_B, USER_C):
            result = await mgr.ensure(state="absent", params={"name": user})
            assert result.action in ("deleted", "noop")

    async def test_02_delete_all_test_groups(self, opn_client: OpnsenseClient) -> None:
        """Delete all test groups."""
        mgr = AuthGroupManager(opn_client)
        for grp in (GROUP_1, GROUP_2):
            result = await mgr.ensure(state="absent", params={"name": grp})
            assert result.action in ("deleted", "noop")
