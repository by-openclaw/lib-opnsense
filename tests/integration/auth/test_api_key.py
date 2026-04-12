# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- auth API key CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/auth/test_api_key.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestApiKeyCRUD.test_01_create_api_key
    2. Idempotent (I)   -- TestApiKeyCRUD.test_02_list_api_keys
    3. Update (U)       -- N/A -- keys have no updatable fields
    4. Check mode (K)   -- TestApiKeyCRUD.test_04_check_mode_delete_all
    5. Read/list (R)    -- covered by test_02_list_api_keys
    6. Ambiguous (A)    -- N/A -- keys are per-user, no match ambiguity
    7. Error (E)        -- TestErrorHandling.test_08_nonexistent_user
    8. Delete (D)       -- TestApiKeyCRUD.test_05_delete_all_keys
    9. Delete noop (Dn) -- TestApiKeyCRUD.test_06_delete_all_keys_idempotent
    10. Cleanup (X)     -- TestCleanup.test_01_delete_test_user

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.auth.api_key import AuthApiKeyManager
from opnsense.managers.auth.user import AuthUserManager

# -- Test data constants -------------------------------------------------------

USER_B = "inttest-bob"

# -- Markers -------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. API Key CRUD
# =============================================================================


class TestApiKeyCRUD:
    """Generate, list, and delete API keys for a test user.

    OPNsense 26.1 API key endpoints use inconsistent identifiers:
        add_api_key/{username}      -- username string
        search_api_key/{any}        -- returns ALL keys (param ignored)
        del_api_key/{id}            -- base64 ID from search results
    """

    async def test_00_setup_user(self, opn_client: OpnsenseClient) -> None:
        """Create the test user for API key operations."""
        mgr = AuthUserManager(opn_client)
        await mgr.ensure(
            state="present",
            params={"name": USER_B, "email": f"{USER_B}@example.com", "password": "T3stP@ss!"},
        )

    async def test_01_create_api_key(self, opn_client: OpnsenseClient) -> None:
        """Generate an API key for bob -- returns key+secret."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.create_key(USER_B)
        assert result.changed is True
        assert result.action == "created"
        assert result.after.get("key"), "API key should be returned"
        assert result.after.get("secret"), "API secret should be returned"

    async def test_02_list_api_keys(self, opn_client: OpnsenseClient) -> None:
        """List API keys for bob -- should have at least 1."""
        mgr = AuthApiKeyManager(opn_client)
        keys = await mgr.list_keys(username=USER_B)
        assert len(keys) >= 1

    async def test_03_create_second_key(self, opn_client: OpnsenseClient) -> None:
        """Create a second API key -- user can have multiple."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.create_key(USER_B)
        assert result.changed is True

    async def test_04_check_mode_delete_all(self, opn_client: OpnsenseClient) -> None:
        """check_mode delete_all -- reports changed but keys still exist."""
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
        """Re-delete all -- noop."""
        mgr = AuthApiKeyManager(opn_client)
        result = await mgr.delete_all_keys(USER_B)
        assert result.changed is False
        assert result.action == "noop"


# =============================================================================
# 2. Error Handling -- API key specific
# =============================================================================


class TestErrorHandling:
    """API key error handling tests."""

    async def test_08_api_key_create_nonexistent_user(self, opn_client: OpnsenseClient) -> None:
        """Creating API key for nonexistent user raises OpnsenseError."""
        from opnsense.exceptions import OpnsenseError

        mgr = AuthApiKeyManager(opn_client)
        try:
            await mgr.create_key("nonexistent-user-99999")
            pytest.fail("Should have raised OpnsenseError")
        except OpnsenseError as exc:
            assert "nonexistent-user-99999" in str(exc)


# =============================================================================
# 3. Cleanup -- delete the test user
# =============================================================================


class TestCleanup:
    """Delete the test user created for API key tests."""

    async def test_01_delete_test_user(self, opn_client: OpnsenseClient) -> None:
        """Delete bob."""
        mgr = AuthUserManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": USER_B})
        assert result.action in ("deleted", "noop")
