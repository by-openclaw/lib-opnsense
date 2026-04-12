# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Syslog destination manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/services/test_syslog_dest.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestSyslogDestCRUD.test_01_create
    2. Idempotent (I)   -- TestSyslogDestCRUD.test_02_idempotent
    3. Update (U)       -- TestSyslogDestCRUD.test_03_update
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_05)
    7. Error (E)        -- N/A -- no FieldValidationError test
    8. Delete (D)       -- TestSyslogDestCRUD.test_04_delete
    9. Delete noop (Dn) -- TestSyslogDestCRUD.test_05_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.services.syslog_dest import SyslogDestManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestSyslogDestCRUD:
    """Syslog destination CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-syslog",
                "hostname": "10.99.99.99",
                "port": "514",
                "transport": "udp4",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-syslog",
                "hostname": "10.99.99.99",
                "port": "514",
                "transport": "udp4",
                "enabled": "0",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-syslog",
                "hostname": "10.99.99.99",
                "port": "1514",
                "transport": "tcp4",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-syslog"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_05_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-syslog"})
        assert r.changed is False
        assert r.action == "noop"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 syslog destination matches description key."""

    DUP_PARAMS = {
        "description": "inttest-dup-syslog",
        "hostname": "10.99.99.98",
        "port": "514",
        "transport": "udp4",
        "enabled": "0",
    }

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two syslog destinations with same description via direct create."""
        mgr = SyslogDestManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = SyslogDestManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_03_ensure_absent_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = SyslogDestManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={"description": "inttest-dup-syslog"},
            )

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """ensure(uuid=) bypasses _find_existing -- works on ambiguous pair."""
        mgr = SyslogDestManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-syslog")
        dups = [r for r in rows if r.get("description") == "inttest-dup-syslog"]
        assert len(dups) == 2
        result = await mgr.ensure(state="present", uuid=dups[0]["uuid"], params=self.DUP_PARAMS)
        assert result.action == "noop"

    async def test_05_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate syslog destinations by UUID."""
        mgr = SyslogDestManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-syslog")
        for r in rows:
            if r.get("description") == "inttest-dup-syslog":
                await mgr.delete(r["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-syslog")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-syslog"]
        assert remaining == []


class TestCheckMode:
    """check_mode on syslog destination create -- resource NOT created."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = SyslogDestManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-syslog-cm",
                "hostname": "10.99.99.97",
                "port": "514",
                "transport": "udp4",
                "enabled": "0",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-syslog-cm")
        found = [row for row in rows if row.get("description") == "inttest-syslog-cm"]
        assert found == []


class TestCleanup:
    """Remove all inttest- syslog destinations."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("syslog/settings/delDestination", row["uuid"])
        await opn_client.reconfigure("syslog/service/reconfigure", timeout=30)
