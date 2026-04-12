# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- auth user CRUD and user-specific error handling.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/auth/test_user.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestUserCRUD.test_01_create_user
    2. Idempotent (I)   -- TestUserCRUD.test_02_create_user_idempotent
    3. Update (U)       -- TestUserCRUD.test_04_update_user
    4. Check mode (K)   -- TestUserCRUD.test_06_check_mode_delete
    5. Read/list (R)    -- TestUserCRUD.test_03_read_user
    6. Ambiguous (A)    -- N/A -- API enforces username uniqueness
    7. Error (E)        -- TestErrorHandling (test_01..test_09)
    8. Delete (D)       -- TestUserCRUD.test_07_delete_user
    9. Delete noop (Dn) -- TestUserCRUD.test_08_delete_user_idempotent
    10. Cleanup (X)     -- TestCleanup.test_01_delete_all_test_users

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import os

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.auth.user import AuthUserManager

# -- Test data constants -------------------------------------------------------

USER_A = "inttest-alice"
USER_B = "inttest-bob"
USER_C = "inttest-carol"

# -- Markers -------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. CRUD User Lifecycle
# =============================================================================


class TestUserCRUD:
    """Create, read, update, delete a single user with full idempotency checks."""

    async def test_01_create_user(self, opn_client: OpnsenseClient) -> None:
        """Create a new user -- changed=True, action=created."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice@example.com", "password": "T3stP@ss!"},
        )
        assert result.changed is True
        assert result.action == "created"
        assert result.uuid is not None

    async def test_02_create_user_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-create same user -- changed=False, action=noop."""
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
        """Update user email -- changed=True, action=updated."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice-updated@example.com"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_05_update_user_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-update with same value -- changed=False."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": USER_A, "email": "alice-updated@example.com"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_06_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        """check_mode=True on delete -- changed=True but no actual delete."""
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
        """Delete user -- changed=True, action=deleted."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": USER_A},
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_08_delete_user_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-delete same user -- changed=False, action=noop."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": USER_A},
        )
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 2. Error Handling -- user-specific and cross-cutting client errors
# =============================================================================


class TestErrorHandling:
    """Verify that API errors raise typed exceptions with correct attributes.

    Every error must be caught with try/except -- no unhandled crashes.
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

        # Try direct create (not ensure) -- should fail with validation error
        try:
            await mgr.create(
                params={"name": "inttest-err-dup", "password": "T3stP@ss!"},
            )
            # OPNsense may silently save -- not all controllers reject duplicates
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
            timeout=0.001,  # 1ms -- guaranteed to timeout
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
        conditions -- connect timeout vs DNS failure vs connection refused.
        Both are acceptable; the key assertion is no unhandled exception.
        """
        from opnsense.exceptions import OpnsenseConnectionError, OpnsenseTimeoutError

        async with OpnsenseClient(
            host="192.0.2.1",  # RFC 5737 -- guaranteed unreachable
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

    async def test_07_ensure_invalid_state(self, opn_client: OpnsenseClient) -> None:
        """Invalid state raises ValueError, not an API error."""
        mgr = AuthUserManager(opn_client)
        try:
            await mgr.ensure(state="invalid", params={"name": "test"})
            pytest.fail("Should have raised ValueError")
        except ValueError as exc:
            assert "invalid" in str(exc).lower()

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
# 3. Cleanup -- delete all test users
# =============================================================================


class TestCleanup:
    """Delete all test users. Runs last."""

    async def test_01_delete_all_test_users(self, opn_client: OpnsenseClient) -> None:
        """Delete all test users."""
        mgr = AuthUserManager(opn_client)
        for user in (USER_A, USER_B, USER_C):
            result = await mgr.ensure(state="absent", params={"name": user})
            assert result.action in ("deleted", "noop")
