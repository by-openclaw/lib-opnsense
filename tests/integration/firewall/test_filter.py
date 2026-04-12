# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall filter rule CRUD, AmbiguousMatch, and error handling.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_filter.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestFilterCRUD.test_01_create_filter_rule
    2. Idempotent (I)   -- TestFilterCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestFilterCRUD.test_03_update_action_to_block
    4. Check mode (K)   -- TestErrorHandling.test_02_check_mode_no_side_effects
    5. Read/list (R)    -- TestFilterCRUD.test_04_list_contains_test_rule
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_05)
    7. Error (E)        -- TestErrorHandling.test_01_invalid_state_raises
    8. Delete (D)       -- TestFilterCRUD.test_05_delete_filter_rule
    9. Delete noop (Dn) -- TestFilterCRUD.test_06_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_filter_rules

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.firewall.alias import FwAliasManager
from opnsense.managers.firewall.filter import FwFilterManager

FILTER_DESC = "inttest-filter-allow-https"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestFilterCRUD:
    """CRUD lifecycle for firewall filter rules."""

    async def test_01_create_filter_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a filter rule allowing HTTPS."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": FILTER_DESC,
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "ipprotocol": "inet",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "0",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": FILTER_DESC,
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "ipprotocol": "inet",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "0",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_action_to_block(self, opn_client: OpnsenseClient) -> None:
        """Update rule action from pass to block -> changed."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": FILTER_DESC,
                "action": "block",
                "interface": "lan",
                "direction": "in",
                "ipprotocol": "inet",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "0",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_list_contains_test_rule(self, opn_client: OpnsenseClient) -> None:
        """Search confirms test rule exists."""
        mgr = FwFilterManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        descriptions = [r.get("description", "") for r in rows]
        assert FILTER_DESC in descriptions

    async def test_05_delete_filter_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the filter rule."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": FILTER_DESC,
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": FILTER_DESC,
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        )
        assert result.changed is False
        assert result.action == "noop"


class TestAmbiguousMatch:
    """Prove AmbiguousMatchError fires on real duplicate data.

    Creates two identical filter rules via direct create() (bypassing ensure),
    then verifies ensure() raises AmbiguousMatchError with both UUIDs.
    Also tests the uuid= escape hatch.
    """

    DUP_PARAMS = {
        "description": "inttest-dup-ambiguous",
        "action": "pass",
        "interface": "lan",
        "direction": "in",
        "protocol": "TCP",
        "destination_port": "443",
        "enabled": "0",
    }

    async def test_01_create_duplicate_rules(self, opn_client: OpnsenseClient) -> None:
        """Create two identical rules via direct create (bypass ensure)."""
        mgr = FwFilterManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = FwFilterManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)

        assert len(exc_info.value.uuids) == 2
        assert exc_info.value.match_keys["description"] == "inttest-dup-ambiguous"
        assert exc_info.value.match_keys["interface"] == "lan"

    async def test_03_ensure_delete_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = FwFilterManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "description": "inttest-dup-ambiguous",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                },
            )

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """ensure(uuid=) bypasses _find_existing -- works on ambiguous pair."""
        mgr = FwFilterManager(opn_client)

        # Get both UUIDs from search
        rows = await mgr.list(search_phrase="inttest-dup-ambiguous")
        dups = [r for r in rows if r.get("description") == "inttest-dup-ambiguous"]
        assert len(dups) == 2

        # Use uuid= to target the first one -- should not raise
        result = await mgr.ensure(
            state="present",
            uuid=dups[0]["uuid"],
            params=self.DUP_PARAMS,
        )
        assert result.action == "noop"

    async def test_05_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate rules by UUID."""
        mgr = FwFilterManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-ambiguous")
        dups = [r for r in rows if r.get("description") == "inttest-dup-ambiguous"]
        for dup in dups:
            await mgr.delete(dup["uuid"])

        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-ambiguous")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-ambiguous"]
        assert remaining == []


class TestErrorHandling:
    """Error handling tests against live device."""

    async def test_01_invalid_state_raises(self, opn_client: OpnsenseClient) -> None:
        """Invalid state raises ValueError."""
        mgr = FwAliasManager(opn_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"name": "test"})

    async def test_02_check_mode_no_side_effects(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> no resource created on device."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "inttest-should-not-exist",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-should-not-exist")
        assert not any(r.get("description") == "inttest-should-not-exist" for r in rows)


class TestCleanup:
    """Final cleanup -- remove any leftover test filter rules."""

    async def test_99_cleanup_filter_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- filter rules."""
        mgr = FwFilterManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
