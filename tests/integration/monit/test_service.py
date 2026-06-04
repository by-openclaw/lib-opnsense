# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — MonitServiceManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/monit/test_service.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestMonitServiceCRUD.test_02_create_service
    2. Idempotent (I)   -- TestMonitServiceCRUD.test_03_idempotent
    3. Update (U)       -- N/A -- conservative flow (no live edit of the service)
    4. Check mode (K)   -- N/A -- create/delete only in this conservative flow
    5. Read/list (R)    -- covered by idempotent (test_03)
    6. Ambiguous (A)    -- N/A -- name is unique per device
    7. Error (E)        -- N/A -- covered by unit tests
    8. Delete (D)       -- TestMonitServiceCRUD.test_04_delete
    9. Delete noop (Dn) -- TestMonitServiceCRUD.test_05_delete_idempotent
    10. Cleanup (X)     -- TestCleanup (services + helper tests)

Notes:
    A Monit service binds a set of tests by UUID. We first create a linkable
    Custom test (``inttest-svctest``), capture its UUID, then create a process
    service that references it via the ``tests`` field.

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import contextlib

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.monit.service import MonitServiceManager
from opnsense.managers.monit.test import MonitTestManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

HELPER_TEST = {
    "name": "inttest-svctest",
    "type": "Custom",
    "condition": "does not exist for 2 cycles",
    "action": "exec",
    "path": "/usr/local/sbin/configctl netflow aggregate start",
}


class TestMonitServiceCRUD:
    """CRUD lifecycle for a Monit process service bound to a helper test."""

    async def test_01_create_helper_test(self, opn_client: OpnsenseClient) -> None:
        """Create the linkable Custom test the service will reference."""
        mgr = MonitTestManager(opn_client)
        r = await mgr.ensure("present", HELPER_TEST)
        assert r.action in ("created", "noop")

    async def test_02_create_service(self, opn_client: OpnsenseClient) -> None:
        """Create a process service referencing the helper test UUID."""
        test_mgr = MonitTestManager(opn_client)
        rows = await test_mgr.list(search_phrase="inttest-svctest")
        helper = [r for r in rows if r.get("name") == "inttest-svctest"]
        assert len(helper) == 1, "Helper test must exist"
        test_uuid = helper[0]["uuid"]

        mgr = MonitServiceManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-svc",
                "type": "process",
                "pidfile": "/tmp/inttest.pid",  # noqa: S108
                "match": "",
                "tests": test_uuid,
            },
        )
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_03_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Re-ensure the same service -> noop."""
        test_mgr = MonitTestManager(opn_client)
        rows = await test_mgr.list(search_phrase="inttest-svctest")
        helper = [r for r in rows if r.get("name") == "inttest-svctest"]
        assert len(helper) == 1
        test_uuid = helper[0]["uuid"]

        mgr = MonitServiceManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-svc",
                "type": "process",
                "pidfile": "/tmp/inttest.pid",  # noqa: S108
                "match": "",
                "tests": test_uuid,
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitServiceManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-svc"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_05_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = MonitServiceManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-svc"})
        assert r.changed is False
        assert r.action == "noop"


class TestCleanup:
    """Remove leftover inttest- services first, then helper tests."""

    async def test_cleanup_services(self, opn_client: OpnsenseClient) -> None:
        """Remove services before tests (services reference test UUIDs)."""
        mgr = MonitServiceManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                with contextlib.suppress(Exception):
                    await mgr.delete(row["uuid"])

    async def test_cleanup_helper_tests(self, opn_client: OpnsenseClient) -> None:
        """Remove the helper Custom test(s)."""
        mgr = MonitTestManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-svctest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                with contextlib.suppress(Exception):
                    await mgr.delete(row["uuid"])
