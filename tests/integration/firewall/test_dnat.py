# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall D-NAT (port forward) CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - OPNsense >= 26.1 (MVC D-NAT controller)
    - Run with: pytest tests/integration/firewall/test_dnat.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestDnatCRUD.test_01_create_dnat_rule
    2. Idempotent (I)   -- TestDnatCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestDnatCRUD.test_03_update_local_port
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_04)
    7. Error (E)        -- TestErrorHandling.test_01_empty_descr_rejected
    8. Delete (D)       -- TestDnatCRUD.test_04_delete_dnat_rule
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_dnat_rules

    SAFETY: ALL D-NAT rules created with disabled=1.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.firewall.dnat import FwDnatManager

DNAT_DESC = "inttest-dnat-forward-http"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDnatCRUD:
    """CRUD lifecycle for D-NAT (port forward) rules. Requires OPNsense >= 26.1.

    SAFETY: ALL rules created with disabled=1. D-NAT apply on WAN crashed
    the FW on 2026-04-05 and 2026-04-07. Disabled rules are safe -- apply
    runs but pf does not load the rule into the ruleset.
    """

    async def test_01_create_dnat_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a D-NAT port forward rule (disabled)."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.11.2.10",
                "local-port": "80",
                "disabled": "1",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.11.2.10",
                "local-port": "80",
                "disabled": "1",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_local_port(self, opn_client: OpnsenseClient) -> None:
        """Update D-NAT local-port -> changed (still disabled).

        Note: ``target`` is a composite match key and cannot be used for
        drift/update tests.  We update ``local-port`` instead.
        """
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.11.2.10",
                "local-port": "8080",
                "disabled": "1",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_dnat_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the D-NAT rule."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "target": "10.11.2.10",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"


class TestCheckMode:
    """Check mode -- ensure(present, check_mode=True) reports changed but does not create."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but D-NAT rule NOT actually created."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "inttest-checkmode-dnat",
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.11.2.99",
                "local-port": "443",
                "disabled": "1",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify the rule was NOT created on the device
        rows = await mgr.list(search_phrase="inttest-checkmode-dnat")
        assert not any(r.get("descr") == "inttest-checkmode-dnat" for r in rows)


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 D-NAT rule matches composite keys.

    Match keys: descr + interface + target.
    Creates two identical D-NAT rules via direct create() (bypassing ensure),
    then verifies ensure() raises AmbiguousMatchError with both UUIDs.
    SAFETY: All rules created with disabled=1.
    """

    DUP_PARAMS = {
        "descr": "inttest-dup-dnat",
        "interface": "wan",
        "ipprotocol": "inet",
        "protocol": "tcp",
        "target": "10.11.2.98",
        "local-port": "80",
        "disabled": "1",
    }

    async def test_01_create_duplicate_rules(self, opn_client: OpnsenseClient) -> None:
        """Create two identical D-NAT rules via direct create (bypass ensure)."""
        mgr = FwDnatManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = FwDnatManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2
        assert exc_info.value.match_keys["descr"] == "inttest-dup-dnat"

    async def test_03_ensure_delete_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = FwDnatManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "descr": "inttest-dup-dnat",
                    "interface": "wan",
                    "target": "10.11.2.98",
                },
            )

    async def test_04_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate D-NAT rules by UUID."""
        mgr = FwDnatManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-dnat")
        dups = [r for r in rows if r.get("descr") == "inttest-dup-dnat"]
        for dup in dups:
            await mgr.delete(dup["uuid"])

        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-dnat")
        remaining = [r for r in rows if r.get("descr") == "inttest-dup-dnat"]
        assert remaining == []


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError.

    SAFETY: All rules created with disabled=1.
    """

    async def test_01_empty_descr_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required descr caught client-side -- FieldValidationError."""
        mgr = FwDnatManager(opn_client)
        with pytest.raises(FieldValidationError, match="descr"):
            await mgr.ensure(
                state="present",
                params={
                    "descr": "",
                    "interface": "wan",
                    "target": "10.11.2.10",
                    "disabled": "1",
                },
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test D-NAT rules."""

    async def test_99_cleanup_dnat_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- D-NAT rules."""
        mgr = FwDnatManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("descr", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
