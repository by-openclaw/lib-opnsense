# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — MonitAlertManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/monit/test_alert.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestMonitAlertCRUD.test_01_create
    2. Idempotent (I)   -- TestMonitAlertCRUD.test_02_idempotent
    3. Update (U)       -- N/A -- conservative flow (no live edit of the alert)
    4. Check mode (K)   -- N/A -- create/delete only in this conservative flow
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- single recipient created
    7. Error (E)        -- N/A -- covered by unit tests
    8. Delete (D)       -- TestMonitAlertCRUD.test_03_delete
    9. Delete noop (Dn) -- TestMonitAlertCRUD.test_04_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup_alerts

Notes:
    The match key is ``recipient``. The alert is created disabled
    (``enabled="0"``) so it never sends live mail.

Naming convention:
    All test objects use prefix 'inttest-' (recipient uses an example.com
    address) to avoid collision with real config.
"""

from __future__ import annotations

import contextlib

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.monit.alert import MonitAlertManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

ALERT_RECIPIENT = "inttest@example.com"

MONIT_ALERT = {
    "name": "x",
    "recipient": ALERT_RECIPIENT,
    "enabled": "0",
    "noton": "0",
    "events": "",
    "reminder": "0",
    "format": "",
    "description": "inttest",
}


class TestMonitAlertCRUD:
    """CRUD lifecycle for a (disabled) Monit alert recipient."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitAlertManager(opn_client)
        r = await mgr.ensure("present", MONIT_ALERT)
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitAlertManager(opn_client)
        r = await mgr.ensure("present", MONIT_ALERT)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitAlertManager(opn_client)
        r = await mgr.ensure("absent", {"recipient": ALERT_RECIPIENT})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_04_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitAlertManager(opn_client)
        r = await mgr.ensure("absent", {"recipient": ALERT_RECIPIENT})
        assert r.changed is False
        assert r.action == "noop"


class TestCleanup:
    """Remove any leftover inttest- Monit alerts."""

    async def test_cleanup_alerts(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitAlertManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("recipient", "")):
                with contextlib.suppress(Exception):
                    await mgr.delete(row["uuid"])
