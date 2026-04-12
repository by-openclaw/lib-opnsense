# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IfBridgeManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/interfaces/test_bridge.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- N/A -- requires spare NICs (test VM has only lan/wan)
    2. Idempotent (I)   -- N/A -- no create available
    3. Update (U)       -- N/A -- no create available
    4. Check mode (K)   -- N/A -- no create available
    5. Read/list (R)    -- N/A -- no create available
    6. Ambiguous (A)    -- N/A -- no create available
    7. Error (E)        -- TestBridgeErrorHandling.test_01 + test_02
    8. Delete (D)       -- N/A -- no create available
    9. Delete noop (Dn) -- N/A -- no create available
    10. Cleanup (X)     -- N/A -- no resources created

    Bridge requires physical interface members not assigned.
    Test VM has only lan (vtnet0) and wan (vtnet1) -- both in use.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.interfaces.bridge import IfBridgeManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestBridgeErrorHandling:
    """Bridge error handling — validate without creating (no spare NICs needed)."""

    async def test_01_missing_members_rejected(self, opn_client: OpnsenseClient) -> None:
        """API rejects bridge without members — OpnsenseValidationError."""
        mgr = IfBridgeManager(opn_client)
        with pytest.raises(OpnsenseValidationError, match="members"):
            await mgr.ensure("present", {"descr": "inttest-bridge-no-members"})

    async def test_02_empty_descr_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required descr caught client-side — FieldValidationError."""
        mgr = IfBridgeManager(opn_client)
        with pytest.raises(FieldValidationError, match="descr"):
            await mgr.ensure("present", {"descr": ""})
