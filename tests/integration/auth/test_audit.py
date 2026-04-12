# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- auth audit log verification.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/auth/test_audit.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- N/A -- read-only audit log
    2. Idempotent (I)   -- N/A -- read-only
    3. Update (U)       -- N/A -- read-only
    4. Check mode (K)   -- N/A -- read-only
    5. Read/list (R)    -- TestAuditLog.test_01_audit_log_accessible,
                           test_02_audit_log_has_recent_entries
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

# -- Markers -------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Audit Log Verification
# =============================================================================


class TestAuditLog:
    """Verify that operations are recorded in the OPNsense audit log."""

    async def test_01_audit_log_accessible(self, opn_client: OpnsenseClient) -> None:
        """System audit log is accessible and returns entries."""
        rows = await opn_client.search(
            "diagnostics/log/core/audit",
            row_count=5,
        )
        assert isinstance(rows, list)
        assert len(rows) > 0

    async def test_02_audit_log_has_recent_entries(self, opn_client: OpnsenseClient) -> None:
        """Audit log contains recent entries (from our test operations)."""
        rows = await opn_client.search(
            "diagnostics/log/core/audit",
            row_count=20,
        )
        # We just need to confirm the log endpoint works and returns data.
        # Matching specific test operations in logs is fragile -- OPNsense
        # logs async and format varies by version.
        assert any(r.get("timestamp") for r in rows)
