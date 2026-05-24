# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — DnsmasqOptionManager against a live OPNsense device.

Safety: tests target DHCPv4 option 252 (proxy-autoconfig URL) on the ``lan``
(OOB) interface with a TEST-NET-1 URL — exotic option number, never collides
with operationally meaningful options. Cleanup scoped to that specific
(interface, option) pair.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.services.dnsmasq_option import DnsmasqOptionManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INTTEST_IFACE = "lan"
INTTEST_OPTION = "252"  # Web Proxy Auto-Discovery (PAC) URL — exotic option


class TestDnsmasqOptionCRUD:
    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqOptionManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "option": INTTEST_OPTION,
                "value": "http://192.0.2.1/inttest.pac",
            },
        )
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqOptionManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "option": INTTEST_OPTION,
                "option6": "",
                "type": "set",
                "value": "http://192.0.2.1/inttest.pac",
            },
        )
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqOptionManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE,
                "option": INTTEST_OPTION,
                "option6": "",
                "type": "set",
                "value": "http://192.0.2.2/inttest.pac",  # changed
            },
        )
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqOptionManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {
                "interface": INTTEST_IFACE,
                "option": INTTEST_OPTION,
                "option6": "",
            },
        )
        assert r.action == "deleted"


class TestFieldValidation:
    async def test_invalid_type_enum(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqOptionManager(opn_client)
        with pytest.raises(FieldValidationError, match="type"):
            await mgr.ensure(
                "present",
                {"option": INTTEST_OPTION, "type": "bogus", "value": "x"},
            )


class TestCleanup:
    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqOptionManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("option") == INTTEST_OPTION and row.get("interface") == INTTEST_IFACE:
                await opn_client.delete("dnsmasq/settings/delOption", row["uuid"])
