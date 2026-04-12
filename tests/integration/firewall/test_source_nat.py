# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall source NAT CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_source_nat.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestSourceNatCRUD.test_01_create_snat_rule
    2. Idempotent (I)   -- TestSourceNatCRUD.test_02_idempotent_noop
    3. Update (U)       -- N/A -- all non-match-key fields optional
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_04)
    7. Error (E)        -- TestErrorHandling.test_01_empty_description
    8. Delete (D)       -- TestSourceNatCRUD.test_03_delete_snat_rule
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_snat_rules

    SAFETY: ALL source NAT rules created with enabled=0.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.firewall.source_nat import FwSourceNatManager

SNAT_DESC = "inttest-snat-masquerade"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestSourceNatCRUD:
    """CRUD lifecycle for source NAT rules.

    SAFETY: ALL rules created with enabled=0. SNAT apply on WAN can
    disrupt routing -- same risk as D-NAT. Disabled rules are safe.
    """

    async def test_01_create_snat_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a source NAT masquerade rule (disabled)."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "source_net": "10.11.3.0/24",
                "target": "wanip",
                "enabled": "0",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "source_net": "10.11.3.0/24",
                "target": "wanip",
                "enabled": "0",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_delete_snat_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the source NAT rule."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "source_net": "10.11.3.0/24",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"


class TestCheckMode:
    """Check mode -- ensure(present, check_mode=True) reports changed but does not create."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but SNAT rule NOT actually created."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "inttest-checkmode-snat",
                "interface": "wan",
                "ipprotocol": "inet",
                "source_net": "10.11.3.128/25",
                "target": "wanip",
                "enabled": "0",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify the rule was NOT created on the device
        rows = await mgr.list(search_phrase="inttest-checkmode-snat")
        assert not any(r.get("description") == "inttest-checkmode-snat" for r in rows)


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 rule matches composite keys.

    Match keys: description + interface + source_net.
    Creates two identical SNAT rules via direct create() (bypassing ensure),
    then verifies ensure() raises AmbiguousMatchError with both UUIDs.
    SAFETY: All rules created with enabled=0.
    """

    DUP_PARAMS = {
        "description": "inttest-dup-snat",
        "interface": "wan",
        "ipprotocol": "inet",
        "source_net": "10.11.3.64/26",
        "target": "wanip",
        "enabled": "0",
    }

    async def test_01_create_duplicate_rules(self, opn_client: OpnsenseClient) -> None:
        """Create two identical SNAT rules via direct create (bypass ensure)."""
        mgr = FwSourceNatManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = FwSourceNatManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2
        assert exc_info.value.match_keys["description"] == "inttest-dup-snat"

    async def test_03_ensure_delete_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = FwSourceNatManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "description": "inttest-dup-snat",
                    "interface": "wan",
                    "source_net": "10.11.3.64/26",
                },
            )

    async def test_04_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate SNAT rules by UUID."""
        mgr = FwSourceNatManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-snat")
        dups = [r for r in rows if r.get("description") == "inttest-dup-snat"]
        for dup in dups:
            await mgr.delete(dup["uuid"])

        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-snat")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-snat"]
        assert remaining == []


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError.

    SAFETY: All rules created with enabled=0.
    """

    async def test_01_empty_description_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required description caught client-side -- FieldValidationError."""
        mgr = FwSourceNatManager(opn_client)
        with pytest.raises(FieldValidationError, match="description"):
            await mgr.ensure(
                state="present",
                params={
                    "description": "",
                    "interface": "wan",
                    "source_net": "10.11.3.0/24",
                    "enabled": "0",
                },
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test source NAT rules."""

    async def test_99_cleanup_snat_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- source NAT rules."""
        mgr = FwSourceNatManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
