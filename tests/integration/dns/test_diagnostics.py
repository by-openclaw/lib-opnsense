# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — UbDiagnosticsManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dns/test_diagnostics.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- N/A -- read-only diagnostics
    2. Idempotent (I)   -- N/A -- read-only
    3. Update (U)       -- N/A -- read-only
    4. Check mode (K)   -- N/A -- read-only
    5. Read/list (R)    -- test_01_get_stats, test_02_get_dnsbl, test_03_list_dnsbl
    6. Ambiguous (A)    -- N/A -- read-only
    7. Error (E)        -- N/A -- read-only
    8. Delete (D)       -- N/A -- read-only
    9. Delete noop (Dn) -- N/A -- read-only
    10. Cleanup (X)     -- N/A -- read-only, no resources created

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.dns.ub_diagnostics import UbDiagnosticsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDiagnostics:
    """Read-only diagnostics — stats and DNSBL config."""

    async def test_01_get_stats(self, opn_client: OpnsenseClient) -> None:
        """Get resolver statistics — must return status=ok."""
        diag = UbDiagnosticsManager(opn_client)
        stats = await diag.get_stats()
        assert stats.get("status") == "ok"
        assert "data" in stats

    async def test_02_get_dnsbl(self, opn_client: OpnsenseClient) -> None:
        """Get DNSBL config — read-only on 26.1.5."""
        diag = UbDiagnosticsManager(opn_client)
        dnsbl = await diag.get_dnsbl()
        assert "enabled" in dnsbl

    async def test_03_list_dnsbl(self, opn_client: OpnsenseClient) -> None:
        """List DNSBL entries via search."""
        diag = UbDiagnosticsManager(opn_client)
        rows = await diag.list_dnsbl()
        assert isinstance(rows, list)
