# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — port field validation via FwFilterManager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_port_validation.py -v

Test flow (cross-cutting: port field validation):
    Not a standard per-manager CRUD lifecycle.
    Tests P01-P09 validate port field acceptance via FwFilterManager.
    1. Create (C)       -- N/A -- cross-cutting validation tests
    2. Idempotent (I)   -- N/A
    3. Update (U)       -- N/A
    4. Check mode (K)   -- N/A
    5. Read/list (R)    -- N/A
    6. Ambiguous (A)    -- N/A
    7. Error (E)        -- test_p02..p03, p07..p09 (rejected ports)
    8. Delete (D)       -- N/A
    9. Delete noop (Dn) -- N/A
    10. Cleanup (X)     -- TestCleanup (rules + aliases)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.firewall.alias import FwAliasManager
from opnsense.managers.firewall.filter import FwFilterManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestPortFieldValidation:
    """Test port field acceptance via FwFilterManager on live device."""

    async def test_p01_single_port(self, opn_client: OpnsenseClient) -> None:
        """Single numeric port accepted."""
        mgr = FwFilterManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-port-single",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "0",
            },
        )
        assert r.changed is True

    async def test_p02_port_range_rejected(self, opn_client: OpnsenseClient) -> None:
        """Port range format rejected by OPNsense filter rules (single port or alias only)."""
        mgr = FwFilterManager(opn_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-port-range",
                    "action": "pass",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "destination_port": "80:443",
                    "enabled": "0",
                },
            )

    async def test_p03_port_list_rejected(self, opn_client: OpnsenseClient) -> None:
        """Comma-separated ports rejected by OPNsense filter rules."""
        mgr = FwFilterManager(opn_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-port-list",
                    "action": "pass",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "destination_port": "80,443,8080",
                    "enabled": "0",
                },
            )

    async def test_p04_port_alias_multi_port(self, opn_client: OpnsenseClient) -> None:
        """Port alias with multiple ports — the OPNsense way to handle port lists.

        OPNsense filter rules reject inline ranges (80:443) and comma lists (80,443).
        The correct pattern: create a port alias with multiple entries, reference by name.
        This is the equivalent of "allow ports 80, 443, 8080" in a single rule.
        """
        # Create port alias with multiple ports (range + list via alias)
        alias_mgr = FwAliasManager(opn_client)
        await alias_mgr.ensure(
            "present",
            {
                "name": "inttest_web_ports",
                "type": "port",
                "content": "80\n443\n8080",
                "description": "Test port alias — multi-port list",
            },
        )
        # Use alias in filter rule — single reference covers all ports
        mgr = FwFilterManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-port-alias",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "inttest_web_ports",
                "enabled": "0",
            },
        )
        assert r.changed is True

    async def test_p04b_port_alias_with_range(self, opn_client: OpnsenseClient) -> None:
        """Port alias containing a range — alias content supports ranges even if rules don't.

        Alias content accepts port ranges (e.g. 8000:8999) when the alias type is "port".
        This gives the range capability that inline port fields lack.
        """
        alias_mgr = FwAliasManager(opn_client)
        await alias_mgr.ensure(
            "present",
            {
                "name": "inttest_range_ports",
                "type": "port",
                "content": "8000:8999",
                "description": "Test port alias — range via alias",
            },
        )
        mgr = FwFilterManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-port-alias-range",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "inttest_range_ports",
                "enabled": "0",
            },
        )
        assert r.changed is True

    async def test_p05_boundary_port_1(self, opn_client: OpnsenseClient) -> None:
        """Port 1 (minimum valid) accepted."""
        mgr = FwFilterManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-port-min",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "1",
                "enabled": "0",
            },
        )
        assert r.changed is True

    async def test_p06_boundary_port_65535(self, opn_client: OpnsenseClient) -> None:
        """Port 65535 (maximum valid) accepted."""
        mgr = FwFilterManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-port-max",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "65535",
                "enabled": "0",
            },
        )
        assert r.changed is True

    async def test_p07_invalid_port_zero(self, opn_client: OpnsenseClient) -> None:
        """Port 0 — no client-side validation (str type), API may accept or reject.

        FwFilterManager uses ``"type": "str"`` for destination_port, so port 0
        passes client validation. This test documents OPNsense API behavior.
        If the API rejects it, OpnsenseValidationError is raised.
        """
        mgr = FwFilterManager(opn_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-port-zero",
                    "action": "pass",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "destination_port": "0",
                    "enabled": "0",
                },
            )

    async def test_p08_invalid_port_negative(self, opn_client: OpnsenseClient) -> None:
        """Negative port — no client-side validation (str type), API should reject.

        Documents OPNsense API behavior for negative port values.
        """
        mgr = FwFilterManager(opn_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-port-negative",
                    "action": "pass",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "destination_port": "-1",
                    "enabled": "0",
                },
            )

    async def test_p09_invalid_port_too_high(self, opn_client: OpnsenseClient) -> None:
        """Port > 65535 — no client-side validation (str type), API should reject.

        Documents OPNsense API behavior for out-of-range port values.
        """
        mgr = FwFilterManager(opn_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-port-toohigh",
                    "action": "pass",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "destination_port": "125657",
                    "enabled": "0",
                },
            )


class TestCleanup:
    """Remove all inttest-port-* rules and test alias."""

    async def test_cleanup_port_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest-port-* filter rules."""
        mgr = FwFilterManager(opn_client)
        for prefix in [
            "inttest-port-single",
            "inttest-port-list",
            "inttest-port-alias",
            "inttest-port-alias-range",
            "inttest-port-min",
            "inttest-port-max",
            "inttest-port-zero",
            "inttest-port-negative",
            "inttest-port-toohigh",
        ]:
            rows = await mgr.list(search_phrase=prefix)
            for r in rows:
                if r.get("description", "").startswith("inttest-port"):
                    await mgr.delete(r["uuid"])

    async def test_cleanup_port_aliases(self, opn_client: OpnsenseClient) -> None:
        """Remove all test port aliases."""
        alias_mgr = FwAliasManager(opn_client)
        await alias_mgr.ensure("absent", {"name": "inttest_web_ports"})
        await alias_mgr.ensure("absent", {"name": "inttest_range_ports"})
