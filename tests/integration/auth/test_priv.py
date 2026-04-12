# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- auth privilege assignment lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/auth/test_priv.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestPrivilegeAssignment.test_01_assign_priv_to_group
    2. Idempotent (I)   -- TestPrivilegeAssignment.test_02_idempotent
    3. Update (U)       -- N/A -- assign/unassign only, no updatable fields
    4. Check mode (K)   -- TestPrivilegeAssignment.test_05_check_mode_unassign
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- server enforces uniqueness
    7. Error (E)        -- TestErrorHandling.test_06_invalid_target_type
    8. Delete (D)       -- TestPrivilegeAssignment.test_06_unassign_priv
    9. Delete noop (Dn) -- TestPrivilegeAssignment.test_07_unassign_idempotent
    10. Cleanup (X)     -- TestCleanup (unassign, delete users, groups)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.auth.group import AuthGroupManager
from opnsense.managers.auth.priv import AuthPrivManager
from opnsense.managers.auth.user import AuthUserManager

# -- Test data constants -------------------------------------------------------

USER_A = "inttest-alice"
USER_B = "inttest-bob"
USER_C = "inttest-carol"

GROUP_1 = "inttest-engineers"
GROUP_2 = "inttest-operators"

PRIV_DIAG = "page-diagnostics-arptable"
PRIV_STATUS = "page-status-interfaces"

# -- Markers -------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Privilege Assignments
# =============================================================================


class TestPrivilegeAssignment:
    """Assign and unassign privileges to groups and users.

    Requires users and groups to exist. Setup creates them inline.
    """

    async def test_00_setup_groups_and_users(self, opn_client: OpnsenseClient) -> None:
        """Create groups and users needed for privilege tests."""
        grp_mgr = AuthGroupManager(opn_client)
        for grp in (GROUP_1, GROUP_2):
            await grp_mgr.ensure(
                state="present",
                params={"name": grp, "description": f"Test group {grp}"},
            )

        usr_mgr = AuthUserManager(opn_client)
        for user in (USER_A, USER_B, USER_C):
            await usr_mgr.ensure(
                state="present",
                params={"name": user, "email": f"{user}@example.com", "password": "T3stP@ss!"},
            )

    async def test_01_assign_priv_to_group(self, opn_client: OpnsenseClient) -> None:
        """Assign diagnostic privilege to engineers group."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_DIAG,
            target_type="group",
            target_name=GROUP_1,
            state="present",
        )
        assert result.changed is True
        assert result.action == "created"

    async def test_02_assign_priv_to_group_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-assign same privilege -- noop."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_DIAG,
            target_type="group",
            target_name=GROUP_1,
            state="present",
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_assign_priv_to_user(self, opn_client: OpnsenseClient) -> None:
        """Assign status privilege directly to alice."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_STATUS,
            target_type="user",
            target_name=USER_A,
            state="present",
        )
        assert result.changed is True
        assert result.action == "created"

    async def test_04_assign_second_priv_to_group(self, opn_client: OpnsenseClient) -> None:
        """Assign status privilege to operators group too."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_STATUS,
            target_type="group",
            target_name=GROUP_2,
            state="present",
        )
        assert result.changed is True
        assert result.action == "created"

    async def test_05_check_mode_unassign(self, opn_client: OpnsenseClient) -> None:
        """check_mode unassign -- reports changed but does not apply."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_DIAG,
            target_type="group",
            target_name=GROUP_1,
            state="absent",
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"

        # Verify privilege is still assigned
        result2 = await mgr.ensure(
            priv_id=PRIV_DIAG,
            target_type="group",
            target_name=GROUP_1,
            state="present",
        )
        assert result2.changed is False  # still assigned

    async def test_06_unassign_priv_from_group(self, opn_client: OpnsenseClient) -> None:
        """Unassign diagnostic privilege from engineers group."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_DIAG,
            target_type="group",
            target_name=GROUP_1,
            state="absent",
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_07_unassign_priv_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-unassign -- noop."""
        mgr = AuthPrivManager(opn_client)
        result = await mgr.ensure(
            priv_id=PRIV_DIAG,
            target_type="group",
            target_name=GROUP_1,
            state="absent",
        )
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 2. Error Handling -- privilege-specific
# =============================================================================


class TestErrorHandling:
    """Privilege-specific error handling tests."""

    async def test_06_privilege_invalid_target_type(self, opn_client: OpnsenseClient) -> None:
        """Invalid target_type raises ValueError, not an API error."""
        mgr = AuthPrivManager(opn_client)
        try:
            await mgr.ensure(
                priv_id="page-all",
                target_type="invalid",
                target_name="test",
            )
            pytest.fail("Should have raised ValueError")
        except ValueError as exc:
            assert "invalid" in str(exc).lower()


# =============================================================================
# 3. Cleanup -- unassign privs, delete users, delete groups
# =============================================================================


class TestCleanup:
    """Remove all privilege assignments, then test users and groups."""

    async def test_01_unassign_all_test_privileges(self, opn_client: OpnsenseClient) -> None:
        """Remove all privilege assignments for test users and groups."""
        mgr = AuthPrivManager(opn_client)
        for priv_id in (PRIV_DIAG, PRIV_STATUS):
            for target_type, targets in [
                ("user", [USER_A, USER_B, USER_C]),
                ("group", [GROUP_1, GROUP_2]),
            ]:
                for target in targets:
                    await mgr.ensure(
                        priv_id=priv_id,
                        target_type=target_type,
                        target_name=target,
                        state="absent",
                    )

    async def test_02_delete_all_test_users(self, opn_client: OpnsenseClient) -> None:
        """Delete all test users (must happen before groups)."""
        mgr = AuthUserManager(opn_client)
        for user in (USER_A, USER_B, USER_C):
            result = await mgr.ensure(state="absent", params={"name": user})
            assert result.action in ("deleted", "noop")

    async def test_03_delete_all_test_groups(self, opn_client: OpnsenseClient) -> None:
        """Delete all test groups."""
        mgr = AuthGroupManager(opn_client)
        for grp in (GROUP_1, GROUP_2):
            result = await mgr.ensure(state="absent", params={"name": grp})
            assert result.action in ("deleted", "noop")
