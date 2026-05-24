# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Dnsmasq domain override manager against a live OPNsense device.

Safety boundaries:
    - All test domains use ``inttest-*.example.com`` (RFC 2606 reserved
      domain — never resolves to real infrastructure).
    - All upstream IPs use ``192.0.2.0/24`` (RFC 5737 TEST-NET-1 — never
      routes).
    - Dnsmasq is currently stopped on the test FW; these are config-only
      entries.
    - Cleanup deletes only entries in the ``inttest-`` namespace.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.services.dnsmasq_domain import DnsmasqDomainManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INTTEST_DOMAIN = "inttest-fwd.example.com"
INTTEST_DOMAIN_DUP = "inttest-dup-fwd.example.com"
INTTEST_IP_1 = "192.0.2.53"
INTTEST_IP_2 = "192.0.2.54"


class TestDnsmasqDomainCRUD:
    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r = await mgr.ensure("present", {"domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1})
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r = await mgr.ensure("present", {"domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1})
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "domain": INTTEST_DOMAIN,
                "ip": INTTEST_IP_1,
                "descr": "updated description",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r = await mgr.ensure(
            "present",
            {"domain": "inttest-cm.example.com", "ip": "192.0.2.99"},
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        rows = await mgr.list()
        assert not any(row.get("domain") == "inttest-cm.example.com" for row in rows), (
            "check_mode must not create"
        )

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r = await mgr.ensure("absent", {"domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r = await mgr.ensure("absent", {"domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1})
        assert r.changed is False
        assert r.action == "noop"


class TestSameDomainDifferentIPs:
    """Composite identity allows same domain forwarded to multiple upstreams."""

    async def test_01_create_two_forwarders_same_domain(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        r1 = await mgr.ensure(
            "present",
            {"domain": "inttest-ha.example.com", "ip": INTTEST_IP_1},
        )
        r2 = await mgr.ensure(
            "present",
            {"domain": "inttest-ha.example.com", "ip": INTTEST_IP_2},
        )
        assert r1.changed is True
        assert r2.changed is True
        assert r1.uuid != r2.uuid

    async def test_02_each_is_independent_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        for ip in (INTTEST_IP_1, INTTEST_IP_2):
            r = await mgr.ensure("present", {"domain": "inttest-ha.example.com", "ip": ip})
            assert r.action == "noop"

    async def test_03_cleanup_pair(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("domain") == "inttest-ha.example.com":
                await mgr.delete(row["uuid"])


class TestAmbiguousMatch:
    """Server permits true duplicates (same domain+ip); library raises."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        dup = {"domain": INTTEST_DOMAIN_DUP, "ip": INTTEST_IP_1}
        r1 = await mgr.create(params=dup)
        r2 = await mgr.create(params=dup)
        assert r1.uuid and r2.uuid and r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure("present", {"domain": INTTEST_DOMAIN_DUP, "ip": INTTEST_IP_1})
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("domain") == INTTEST_DOMAIN_DUP:
                await mgr.delete(row["uuid"])


class TestFieldValidation:
    async def test_01_missing_domain(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        with pytest.raises(FieldValidationError, match="domain"):
            await mgr.ensure("present", {"ip": INTTEST_IP_1})

    async def test_02_missing_ip(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        with pytest.raises(FieldValidationError, match="ip"):
            await mgr.ensure("present", {"domain": INTTEST_DOMAIN})


class TestCleanup:
    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqDomainManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            d = row.get("domain", "")
            if d.startswith("inttest-"):
                await opn_client.delete("dnsmasq/settings/delDomain", row["uuid"])
        await opn_client.reconfigure("dnsmasq/service/reconfigure", timeout=15)
