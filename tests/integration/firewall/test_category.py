# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall category CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_category.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestCategoryCRUD.test_01_create_category
    2. Idempotent (I)   -- TestCategoryCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestCategoryCRUD.test_03_update_color
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- API enforces category name uniqueness
    7. Error (E)        -- TestErrorHandling.test_01_empty_name_rejected
    8. Delete (D)       -- TestCategoryCRUD.test_04_delete_category
    9. Delete noop (Dn) -- TestCategoryCRUD.test_05_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_categories

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.firewall.category import FwCategoryManager

CATEGORY_NAME = "inttest-category"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestCategoryCRUD:
    """CRUD lifecycle for firewall categories. No apply needed."""

    async def test_01_create_category(self, opn_client: OpnsenseClient) -> None:
        """Create a category."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": CATEGORY_NAME, "color": "ff0000"},
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": CATEGORY_NAME, "color": "ff0000"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_color(self, opn_client: OpnsenseClient) -> None:
        """Update color -> changed."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": CATEGORY_NAME, "color": "00ff00"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_category(self, opn_client: OpnsenseClient) -> None:
        """Delete category."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": CATEGORY_NAME})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_05_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": CATEGORY_NAME})
        assert result.changed is False
        assert result.action == "noop"


class TestCheckMode:
    """Check mode -- ensure(present, check_mode=True) reports changed but does not create."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but category NOT actually created."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "inttest-checkmode-cat", "color": "aabbcc"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify the category was NOT created on the device
        rows = await mgr.list(search_phrase="inttest-checkmode-cat")
        assert not any(r.get("name") == "inttest-checkmode-cat" for r in rows)


# Ambiguous match: N/A — OPNsense enforces category name uniqueness at API level.
# Direct create() with duplicate name returns validation error:
# "A category with this name already exists."


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError."""

    async def test_01_empty_name_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required name caught client-side -- FieldValidationError."""
        mgr = FwCategoryManager(opn_client)
        with pytest.raises(FieldValidationError, match="name"):
            await mgr.ensure(
                state="present",
                params={"name": "", "color": "ff0000"},
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test categories."""

    async def test_99_cleanup_categories(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- categories."""
        mgr = FwCategoryManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("name", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
