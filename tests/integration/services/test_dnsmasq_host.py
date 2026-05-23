# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Dnsmasq host manager against a live OPNsense device.

Safety boundaries:
    - Every test entry uses the ``inttest-`` hostname prefix and the
      ``inttest.example.com`` domain — guaranteed not to clash with real
      records on the test FW.
    - IPs use the documentation range ``192.0.2.0/24`` (RFC 5737 TEST-NET-1)
      so the entries describe non-routable demo addresses. Even if
      dnsmasq were enabled and someone queried them, the answer points
      nowhere reachable on our networks.
    - Cleanup deletes every entry whose domain is ``inttest.example.com``.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.services.dnsmasq_host import DnsmasqHostManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INTTEST_DOMAIN = "inttest.example.com"
INTTEST_HOST = "inttest-host-01"
INTTEST_HOST_DUP = "inttest-dup-host"
INTTEST_IP_1 = "192.0.2.10"
INTTEST_IP_2 = "192.0.2.11"


class TestDnsmasqHostCRUD:
    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        r = await mgr.ensure(
            "present",
            {"host": INTTEST_HOST, "domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1},
        )
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        r = await mgr.ensure(
            "present",
            {"host": INTTEST_HOST, "domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1},
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        r = await mgr.ensure(
            "present",
            {"host": INTTEST_HOST, "domain": INTTEST_DOMAIN, "ip": INTTEST_IP_2},
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "host": "inttest-cm-host",
                "domain": INTTEST_DOMAIN,
                "ip": "192.0.2.99",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        rows = await mgr.list()
        assert not any(row.get("host") == "inttest-cm-host" for row in rows), (
            "check_mode must not create"
        )

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        r = await mgr.ensure("absent", {"host": INTTEST_HOST, "domain": INTTEST_DOMAIN})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        r = await mgr.ensure("absent", {"host": INTTEST_HOST, "domain": INTTEST_DOMAIN})
        assert r.changed is False
        assert r.action == "noop"


class TestAmbiguousMatch:
    """Server permits duplicates on host+domain — ambiguity surfaces in lib."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        dup_params = {
            "host": INTTEST_HOST_DUP,
            "domain": INTTEST_DOMAIN,
            "ip": "192.0.2.20",
        }
        r1 = await mgr.create(params=dup_params)
        r2 = await mgr.create(params=dup_params)
        assert r1.uuid and r2.uuid and r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                {
                    "host": INTTEST_HOST_DUP,
                    "domain": INTTEST_DOMAIN,
                    "ip": "192.0.2.20",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("host") == INTTEST_HOST_DUP and row.get("domain") == INTTEST_DOMAIN:
                await mgr.delete(row["uuid"])


class TestFieldValidation:
    async def test_01_missing_host(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        with pytest.raises(FieldValidationError, match="host"):
            await mgr.ensure("present", {"domain": INTTEST_DOMAIN, "ip": INTTEST_IP_1})

    async def test_02_missing_domain(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        with pytest.raises(FieldValidationError, match="domain"):
            await mgr.ensure("present", {"host": INTTEST_HOST, "ip": INTTEST_IP_1})


class TestCleanup:
    """Remove every entry in the inttest domain."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqHostManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("domain") == INTTEST_DOMAIN:
                await opn_client.delete("dnsmasq/settings/delHost", row["uuid"])
        await opn_client.reconfigure("dnsmasq/service/reconfigure", timeout=15)
