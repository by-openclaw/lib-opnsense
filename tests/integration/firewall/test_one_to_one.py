# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall 1:1 NAT (BINAT) CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_one_to_one.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestOneToOneCRUD.test_01_create_rule
    2. Idempotent (I)   -- TestOneToOneCRUD.test_02_idempotent_noop
    3. Update (U)       -- N/A -- all non-match-key fields optional
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_04)
    7. Error (E)        -- TestErrorHandling.test_01_empty_description
    8. Delete (D)       -- TestOneToOneCRUD.test_03_delete_rule
    9. Delete noop (Dn) -- TestOneToOneCRUD.test_04_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_one_to_one_rules

    SAFETY: ALL 1:1 NAT rules created with disabled=1.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.firewall.one_to_one import FwOneToOneManager

ONETOONE_DESC = "inttest-1to1-binat"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestOneToOneCRUD:
    """CRUD lifecycle for 1:1 NAT (BINAT) rules.

    SAFETY: ALL rules created with disabled=1.
    """

    async def test_01_create_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a 1:1 NAT rule (disabled)."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "type": "binat",
                "external": "10.11.1.200",
                "source_net": "10.11.2.10/32",
                "disabled": "1",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "type": "binat",
                "external": "10.11.1.200",
                "source_net": "10.11.2.10/32",
                "disabled": "1",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_delete_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the 1:1 NAT rule."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "source_net": "10.11.2.10/32",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_04_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "source_net": "10.11.2.10/32",
            },
        )
        assert result.changed is False
        assert result.action == "noop"


class TestCheckMode:
    """Check mode -- ensure(present, check_mode=True) reports changed but does not create."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but 1:1 NAT rule NOT actually created."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "inttest-checkmode-1to1",
                "interface": "wan",
                "type": "binat",
                "external": "10.11.1.201",
                "source_net": "10.11.2.99/32",
                "disabled": "1",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify the rule was NOT created on the device
        rows = await mgr.list(search_phrase="inttest-checkmode-1to1")
        assert not any(r.get("description") == "inttest-checkmode-1to1" for r in rows)


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 rule matches composite keys.

    Match keys: description + interface + source_net.
    Creates two identical 1:1 NAT rules via direct create() (bypassing ensure),
    then verifies ensure() raises AmbiguousMatchError with both UUIDs.
    SAFETY: All rules created with disabled=1.
    """

    DUP_PARAMS = {
        "description": "inttest-dup-1to1",
        "interface": "wan",
        "type": "binat",
        "external": "10.11.1.202",
        "source_net": "10.11.2.97/32",
        "disabled": "1",
    }

    async def test_01_create_duplicate_rules(self, opn_client: OpnsenseClient) -> None:
        """Create two identical 1:1 NAT rules via direct create (bypass ensure)."""
        mgr = FwOneToOneManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = FwOneToOneManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2
        assert exc_info.value.match_keys["description"] == "inttest-dup-1to1"

    async def test_03_ensure_delete_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = FwOneToOneManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "description": "inttest-dup-1to1",
                    "interface": "wan",
                    "source_net": "10.11.2.97/32",
                },
            )

    async def test_04_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate 1:1 NAT rules by UUID."""
        mgr = FwOneToOneManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-1to1")
        dups = [r for r in rows if r.get("description") == "inttest-dup-1to1"]
        for dup in dups:
            await mgr.delete(dup["uuid"])

        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-1to1")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-1to1"]
        assert remaining == []


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError.

    SAFETY: All rules created with disabled=1.
    """

    async def test_01_empty_description_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required description caught client-side -- FieldValidationError."""
        mgr = FwOneToOneManager(opn_client)
        with pytest.raises(FieldValidationError, match="description"):
            await mgr.ensure(
                state="present",
                params={
                    "description": "",
                    "interface": "wan",
                    "source_net": "10.11.2.10/32",
                    "disabled": "1",
                },
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test 1:1 NAT rules."""

    async def test_99_cleanup_one_to_one_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- 1:1 NAT rules."""
        mgr = FwOneToOneManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
