# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — MonitTestManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/monit/test_test.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestMonitTestCRUD.test_01_create
    2. Idempotent (I)   -- TestMonitTestCRUD.test_02_idempotent
    3. Update (U)       -- N/A -- conservative flow (no live edit of the test)
    4. Check mode (K)   -- N/A -- create/delete only in this conservative flow
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- name is unique per device
    7. Error (E)        -- N/A -- covered by unit tests
    8. Delete (D)       -- TestMonitTestCRUD.test_03_delete
    9. Delete noop (Dn) -- TestMonitTestCRUD.test_04_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup_tests

Notes:
    ``type`` must be ``"Custom"`` for a free-text condition+action test;
    OPNsense refuses to change the ``type`` of a test that is linked to a
    service, so a standalone Custom test is the safe, idempotent shape.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import contextlib

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.monit.test import MonitTestManager
from tests.integration.monit import SAFE_EXEC_PATH, assert_monit_healthy

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# exec path is single-token on purpose: a multi-word command breaks monitrc
# parsing and crash-loops the daemon. Real multi-arg heals use a seed-owned
# wrapper script; see SAFE_EXEC_PATH docstring.
MONIT_TEST = {
    "name": "inttest-heal",
    "type": "Custom",
    "condition": "does not exist for 2 cycles",
    "action": "exec",
    "path": SAFE_EXEC_PATH,
}


class TestMonitTestCRUD:
    """CRUD lifecycle for a Monit Custom test definition."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitTestManager(opn_client)
        r = await mgr.ensure("present", MONIT_TEST)
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid
        # reconfigure regenerated monitrc + restarted the daemon — verify it
        # survived (a bad exec would crash-loop monit, invisible to the API).
        await assert_monit_healthy(opn_client)

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitTestManager(opn_client)
        r = await mgr.ensure("present", MONIT_TEST)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitTestManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-heal"})
        assert r.changed is True
        assert r.action == "deleted"
        await assert_monit_healthy(opn_client)

    async def test_04_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitTestManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-heal"})
        assert r.changed is False
        assert r.action == "noop"


class TestCleanup:
    """Remove any leftover inttest- Monit tests."""

    async def test_cleanup_tests(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitTestManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                with contextlib.suppress(Exception):
                    await mgr.delete(row["uuid"])
