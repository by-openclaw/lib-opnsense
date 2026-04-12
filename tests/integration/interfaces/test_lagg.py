# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfLaggManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Device must have unassigned physical interfaces for LAGG members
    - Run with: pytest tests/integration/interfaces/test_lagg.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- N/A -- requires unassigned NICs (test VM has only lan/wan)
    2. Idempotent (I)   -- N/A -- no create available
    3. Update (U)       -- N/A -- no create available
    4. Check mode (K)   -- N/A -- no create available
    5. Read/list (R)    -- N/A -- no create available
    6. Ambiguous (A)    -- N/A -- API enforces uniqueness on descr
    7. Error (E)        -- TestLaggErrorHandling.test_01 + test_02
    8. Delete (D)       -- N/A -- no create available
    9. Delete noop (Dn) -- N/A -- no create available
    10. Cleanup (X)     -- N/A -- no resources created

    LAGG requires physical NIC members not assigned to any interface.
    Test VM has only vtnet0 (LAN) and vtnet1 (WAN) -- both in use.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.interfaces.lagg import IfLaggManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestLaggErrorHandling:
    """LAGG error handling — validate without creating (no spare NICs needed)."""

    async def test_01_missing_members_rejected(self, opn_client: OpnsenseClient) -> None:
        """API rejects LAGG without members — OpnsenseValidationError."""
        mgr = IfLaggManager(opn_client)
        with pytest.raises(OpnsenseValidationError, match="members"):
            await mgr.ensure("present", {"descr": "inttest-lagg-no-members", "proto": "none"})

    async def test_02_bad_proto_enum(self, opn_client: OpnsenseClient) -> None:
        """Invalid proto enum caught client-side — FieldValidationError."""
        mgr = IfLaggManager(opn_client)
        with pytest.raises(FieldValidationError, match="proto"):
            await mgr.ensure("present", {"descr": "inttest-lagg-bad", "proto": "invalid"})
