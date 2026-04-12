# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — RtGatewayManager CRUD lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/routing/test_gateway.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestGatewayCRUD.test_01_create_gateway
    2. Idempotent (I)   -- TestGatewayCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestGatewayCRUD.test_03_update_descr
    4. Check mode (K)   -- TestGatewayCRUD.test_04_check_mode_delete
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- API enforces gateway name uniqueness
    7. Error (E)        -- TestErrorHandling.test_07_empty_name_raises
    8. Delete (D)       -- TestGatewayCRUD.test_05_delete_gateway
    9. Delete noop (Dn) -- TestGatewayCRUD.test_06_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_gateways

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.routing.gateway import RtGatewayManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

GW_PARAMS = {
    "name": "inttest-gw-test",
    "interface": "lan",
    "gateway": "10.11.99.254",
    "disabled": "1",
    "monitor_disable": "1",
}


class TestGatewayCRUD:
    """Gateway CRUD lifecycle — safe with disabled + monitor_disable."""

    async def test_01_create_gateway(self, opn_client: OpnsenseClient) -> None:
        """Create a test gateway on LAN, disabled with monitoring off."""
        mgr = RtGatewayManager(opn_client)
        result = await mgr.ensure(state="present", params=GW_PARAMS)
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = RtGatewayManager(opn_client)
        result = await mgr.ensure(state="present", params=GW_PARAMS)
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_descr(self, opn_client: OpnsenseClient) -> None:
        """Update description -> changed."""
        mgr = RtGatewayManager(opn_client)
        updated = {**GW_PARAMS, "descr": "inttest-gw-updated"}
        result = await mgr.ensure(state="present", params=updated)
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        """check_mode delete -> changed=True but resource NOT deleted."""
        mgr = RtGatewayManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "inttest-gw-test"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"

        # Verify it was NOT actually deleted
        rows = await mgr.list(search_phrase="inttest-gw-test")
        assert any(r.get("name") == "inttest-gw-test" for r in rows)

    async def test_05_delete_gateway(self, opn_client: OpnsenseClient) -> None:
        """Delete the test gateway."""
        mgr = RtGatewayManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "inttest-gw-test"},
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = RtGatewayManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "inttest-gw-test"},
        )
        assert result.changed is False
        assert result.action == "noop"


class TestErrorHandling:
    """Field validation error tests."""

    async def test_07_empty_name_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty name (required field) -> FieldValidationError."""
        mgr = RtGatewayManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                state="present",
                params={"name": "", "interface": "lan", "gateway": "10.11.99.253"},
            )


class TestCleanup:
    """Final cleanup — remove any leftover test gateways."""

    async def test_99_cleanup_gateways(self, opn_client: OpnsenseClient) -> None:
        mgr = RtGatewayManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("name", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
