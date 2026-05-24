# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — DnsmasqBootManager against a live OPNsense device.

Safety: test entries use filename ``inttest-pxe-*`` on the ``lan`` (OOB)
interface — never collides with real PXE config; cleanup scoped to the
``inttest-pxe`` prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.services.dnsmasq_boot import DnsmasqBootManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INTTEST_IFACE = "lan"
INTTEST_FILE = "inttest-pxe-loader.0"
INTTEST_PREFIX = "inttest-pxe"


class TestDnsmasqBootCRUD:
    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqBootManager(opn_client)
        r = await mgr.ensure("present", {"interface": INTTEST_IFACE, "filename": INTTEST_FILE})
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqBootManager(opn_client)
        r = await mgr.ensure("present", {"interface": INTTEST_IFACE, "filename": INTTEST_FILE})
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqBootManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "filename": INTTEST_FILE,
                "description": "updated",
            },
        )
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqBootManager(opn_client)
        r = await mgr.ensure("absent", {"interface": INTTEST_IFACE, "filename": INTTEST_FILE})
        assert r.action == "deleted"


class TestFieldValidation:
    async def test_missing_filename(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqBootManager(opn_client)
        with pytest.raises(FieldValidationError, match="filename"):
            await mgr.ensure("present", {"interface": INTTEST_IFACE})


class TestCleanup:
    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqBootManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("filename", "").startswith(INTTEST_PREFIX):
                await opn_client.delete("dnsmasq/settings/delBoot", row["uuid"])
