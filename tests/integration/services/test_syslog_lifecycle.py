# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Syslog destination manager on live OPNsense device.

All destinations created disabled with inttest- prefix and fake target IP.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
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


class TestCleanup:
    """Remove all inttest- syslog destinations."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = SyslogDestManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("syslog/settings/delDestination", row["uuid"])
        await opn_client.reconfigure("syslog/service/reconfigure", timeout=30)
