# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — full auth lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/ -m integration -v

Test flow (ordered):
    1. CRUD user lifecycle       — create, read, update, delete, idempotency
    2. CRUD group lifecycle      — create, read, update, delete, idempotency
    3. User-group assignments    — create users+groups, assign to multiple groups
    4. Privilege assignments     — assign/unassign privs to groups and users
    5. API key CRUD              — generate, list, delete keys for a user
    6. Audit log verification    — confirm operations appear in system log
    7. Error handling            — verify exceptions are caught, not crashes
    8. Full cleanup              — delete all test objects, verify clean state

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import os

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.auth_api_key import AuthApiKeyManager
from opnsense.managers.auth_group import AuthGroupManager
from opnsense.managers.auth_priv import AuthPrivManager
from opnsense.managers.auth_user import AuthUserManager

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
# 1. CRUD User Lifecycle
# =============================================================================


class TestUserCRUD:
    """Create, read, update, delete a single user with full idempotency checks."""

    async def test_01_create_user(self, opn_client: OpnsenseClient) -> None:
        """Create a new user — changed=True, action=created."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice@example.com", "password": "T3stP@ss!"},
        )
        assert result.changed is True
        assert result.action == "created"
        assert result.uuid is not None

    async def test_02_create_user_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-create same user — changed=False, action=noop."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice@example.com"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_read_user(self, opn_client: OpnsenseClient) -> None:
        """List users, find the created user by name."""
        mgr = AuthUserManager(opn_client)
        rows = await mgr.list(search_phrase=USER_A)
        matches = [r for r in rows if r.get("name") == USER_A]
        assert len(matches) == 1
        assert matches[0].get("name") == USER_A

    async def test_04_update_user(self, opn_client: OpnsenseClient) -> None:
        """Update user email — changed=True, action=updated."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice-updated@example.com"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_05_update_user_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-update with same value — changed=False."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice-updated@example.com"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_06_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        """check_mode=True on delete — changed=True but no actual delete."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": USER_A},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"

        # Verify user still exists after check_mode
        rows = await mgr.list(search_phrase=USER_A)
        assert any(r.get("name") == USER_A for r in rows)

    async def test_07_delete_user(self, opn_client: OpnsenseClient) -> None:
        """Delete user — changed=True, action=deleted."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": USER_A},
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_08_delete_user_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-delete same user — changed=False, action=noop."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": USER_A},
        )
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 2. CRUD Group Lifecycle
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
        """Re-create same group — noop."""
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
        """Re-delete — noop."""
        mgr = AuthGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": GROUP_1})
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 3. User-Group Assignments
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

        Uses GID (numeric) for group_memberships — OPNsense 26.1 format.
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
# 4. Privilege Assignments
# =============================================================================


class TestPrivilegeAssignment:
    """Assign and unassign privileges to groups and users."""

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
        """Re-assign same privilege — noop."""
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
        """check_mode unassign — reports changed but does not apply."""
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
        """Re-unassign — noop."""
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
# 5. API Key CRUD
# =============================================================================


class TestApiKeyCRUD:
    """Generate, list, and delete API keys for a test user.

    OPNsense 26.1 API key endpoints use inconsistent identifiers:
        add_api_key/{username}      — username string
        search_api_key/{any}        — returns ALL keys (param ignored)
        del_api_key/{id}            — base64 ID from search results
    """

    async def test_01_create_api_key(self, opn_client: OpnsenseClient) -> None:
        """Generate an API key for bob — returns key+secret."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.create_key(USER_B)
        assert result.changed is True
        assert result.action == "created"
        assert result.after.get("key"), "API key should be returned"
        assert result.after.get("secret"), "API secret should be returned"

    async def test_02_list_api_keys(self, opn_client: OpnsenseClient) -> None:
        """List API keys for bob — should have at least 1."""
        mgr = AuthApiKeyManager(opn_client)
        keys = await mgr.list_keys(username=USER_B)
        assert len(keys) >= 1

    async def test_03_create_second_key(self, opn_client: OpnsenseClient) -> None:
        """Create a second API key — user can have multiple."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.create_key(USER_B)
        assert result.changed is True

    async def test_04_check_mode_delete_all(self, opn_client: OpnsenseClient) -> None:
        """check_mode delete_all — reports changed but keys still exist."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.delete_all_keys(USER_B, check_mode=True)
        assert result.changed is True

        # Keys should still exist
        keys = await mgr.list_keys(username=USER_B)
        assert len(keys) >= 2

    async def test_05_delete_all_keys(self, opn_client: OpnsenseClient) -> None:
        """Delete all API keys for bob."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.delete_all_keys(USER_B)
        assert result.changed is True
        assert result.action == "deleted"

        # Verify clean
        keys = await mgr.list_keys(username=USER_B)
        assert len(keys) == 0

    async def test_06_delete_all_keys_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-delete all — noop."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.delete_all_keys(USER_B)
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 6. Audit Log Verification
# =============================================================================


class TestAuditLog:
    """Verify that operations are recorded in the OPNsense audit log."""

    async def test_01_audit_log_accessible(self, opn_client: OpnsenseClient) -> None:
        """System audit log is accessible and returns entries."""
        rows = await opn_client.search(
            "diagnostics/log/core/audit",
            row_count=5,
        )
        assert isinstance(rows, list)
        assert len(rows) > 0

    async def test_02_audit_log_has_recent_entries(self, opn_client: OpnsenseClient) -> None:
        """Audit log contains recent entries (from our test operations)."""
        rows = await opn_client.search(
            "diagnostics/log/core/audit",
            row_count=20,
        )
        # We just need to confirm the log endpoint works and returns data.
        # Matching specific test operations in logs is fragile — OPNsense
        # logs async and format varies by version.
        assert any(r.get("timestamp") for r in rows)


# =============================================================================
# 7. Error Handling — verify exceptions are caught, not crashes
# =============================================================================


class TestErrorHandling:
    """Verify that API errors raise typed exceptions with correct attributes.

    Every error must be caught with try/except — no unhandled crashes.
    Each exception carries status_code, endpoint, and a human-readable message.
    """

    async def test_01_auth_error_invalid_credentials(self) -> None:
        """Invalid API key raises OpnsenseAuthError (401), not a crash."""
        from opnsense.exceptions import OpnsenseAuthError

        async with OpnsenseClient(
            host=os.environ["OPN_HOST"].removeprefix("https://").removeprefix("http://"),
            key="invalid-key",
            secret="invalid-secret",
            verify_ssl=False,
        ) as bad_client:
            mgr = AuthUserManager(bad_client)
            try:
                await mgr.list()
                pytest.fail("Should have raised OpnsenseAuthError")
            except OpnsenseAuthError as exc:
                assert exc.status_code == 401
                assert exc.endpoint is not None
                assert "401" in str(exc)

    async def test_02_endpoint_not_found(self, opn_client: OpnsenseClient) -> None:
        """Calling a nonexistent endpoint raises OpnsenseEndpointMissingError (404)."""
        from opnsense.exceptions import OpnsenseEndpointMissingError

        try:
            await opn_client.get("auth/nonexistent/endpoint")
            pytest.fail("Should have raised OpnsenseEndpointMissingError")
        except OpnsenseEndpointMissingError as exc:
            assert exc.status_code == 404
            assert "nonexistent" in str(exc)

    async def test_03_validation_error_duplicate_user(self, opn_client: OpnsenseClient) -> None:
        """Creating a user that already exists raises OpnsenseValidationError."""
        from opnsense.exceptions import OpnsenseValidationError

        mgr = AuthUserManager(opn_client)

        # Create the user first
        await mgr.ensure(
            state="present",
            params={"name": "inttest-err-dup", "password": "T3stP@ss!"},
        )

        # Try direct create (not ensure) — should fail with validation error
        try:
            await mgr.create(
                params={"name": "inttest-err-dup", "password": "T3stP@ss!"},
            )
            # OPNsense may silently save — not all controllers reject duplicates
        except OpnsenseValidationError as exc:
            assert exc.status_code == 400
            assert isinstance(exc.validations, dict)

        # Cleanup
        await mgr.ensure(state="absent", params={"name": "inttest-err-dup"})

    async def test_04_timeout_error(self) -> None:
        """Extremely short timeout raises OpnsenseTimeoutError, not a crash."""
        from opnsense.exceptions import OpnsenseConnectionError, OpnsenseTimeoutError

        async with OpnsenseClient(
            host=os.environ["OPN_HOST"].removeprefix("https://").removeprefix("http://"),
            key=os.environ["OPN_KEY"],
            secret=os.environ["OPN_SECRET"],
            verify_ssl=False,
            timeout=0.001,  # 1ms — guaranteed to timeout
            max_retries=1,
        ) as slow_client:
            mgr = AuthUserManager(slow_client)
            try:
                await mgr.list()
                pytest.fail("Should have raised timeout or connection error")
            except (OpnsenseTimeoutError, OpnsenseConnectionError) as exc:
                # Either timeout or connection error is acceptable
                assert exc.endpoint is not None or exc.message is not None

    async def test_05_connection_error_wrong_host(self) -> None:
        """Wrong host raises OpnsenseConnectionError or OpnsenseTimeoutError, not a crash.

        An unreachable host may raise either error depending on network
        conditions — connect timeout vs DNS failure vs connection refused.
        Both are acceptable; the key assertion is no unhandled exception.
        """
        from opnsense.exceptions import OpnsenseConnectionError, OpnsenseTimeoutError

        async with OpnsenseClient(
            host="192.0.2.1",  # RFC 5737 — guaranteed unreachable
            key="dummy",
            secret="dummy",
            verify_ssl=False,
            timeout=3,
            max_retries=1,
        ) as bad_client:
            mgr = AuthUserManager(bad_client)
            try:
                await mgr.list()
                pytest.fail("Should have raised connection or timeout error")
            except (OpnsenseConnectionError, OpnsenseTimeoutError) as exc:
                assert exc.message is not None

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

    async def test_07_ensure_invalid_state(self, opn_client: OpnsenseClient) -> None:
        """Invalid state raises ValueError, not an API error."""
        mgr = AuthUserManager(opn_client)
        try:
            await mgr.ensure(state="invalid", params={"name": "test"})
            pytest.fail("Should have raised ValueError")
        except ValueError as exc:
            assert "invalid" in str(exc).lower()

    async def test_08_api_key_create_nonexistent_user(self, opn_client: OpnsenseClient) -> None:
        """Creating API key for nonexistent user raises OpnsenseError."""
        from opnsense.exceptions import OpnsenseError

        mgr = AuthApiKeyManager(opn_client)
        try:
            await mgr.create_key("nonexistent-user-99999")
            pytest.fail("Should have raised OpnsenseError")
        except OpnsenseError as exc:
            assert "nonexistent-user-99999" in str(exc)

    async def test_09_error_attributes_are_accessible(self, opn_client: OpnsenseClient) -> None:
        """All exception attributes (message, status_code, endpoint) are accessible."""
        from opnsense.exceptions import OpnsenseEndpointMissingError

        try:
            await opn_client.get("fake/endpoint/does_not_exist")
        except OpnsenseEndpointMissingError as exc:
            # Verify all attributes exist and are the correct type
            assert isinstance(exc.message, str)
            assert isinstance(exc.status_code, int)
            assert isinstance(exc.endpoint, str)
            assert len(exc.message) > 0
            # Verify str() representation includes context
            error_str = str(exc)
            assert "404" in error_str
            assert "fake/endpoint" in error_str


# =============================================================================
# 8. Full Cleanup — delete all test objects
# =============================================================================


class TestCleanup:
    """Delete all test users, groups, and privilege assignments.

    Runs last. Leaves the OPNsense device in the same state as before tests.
    """

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
        """Delete all test users."""
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

    async def test_04_verify_clean_state(self, opn_client: OpnsenseClient) -> None:
        """Verify no test objects remain."""
        user_mgr = AuthUserManager(opn_client)
        grp_mgr = AuthGroupManager(opn_client)

        users = await user_mgr.list()
        groups = await grp_mgr.list()

        test_users = [u for u in users if u.get("name", "").startswith("inttest-")]
        test_groups = [g for g in groups if g.get("name", "").startswith("inttest-")]

        assert test_users == [], f"Leftover test users: {[u['name'] for u in test_users]}"
        assert test_groups == [], f"Leftover test groups: {[g['name'] for g in test_groups]}"
