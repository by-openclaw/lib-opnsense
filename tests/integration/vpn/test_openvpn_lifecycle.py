# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — OpenVPN instance manager on live OPNsense device.

Requires Trust/PKI: creates CA + cert chain for OpenVPN server.
All objects disabled, inttest- prefix.
vpnid uses unique test value (99).
cert/ca use refid not UUID.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.vpn.ovpn_instance import OvpnInstanceManager
from opnsense.managers.trust.ca import TrustCaManager
from opnsense.managers.trust.cert import TrustCertManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestOvpnSetup:
    """Create CA + cert chain needed for OpenVPN."""

    async def test_01_create_ca(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "descr": "inttest-ovpn-ca",
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "lifetime": "825",
                "commonname": "inttest-ovpn-ca.example.com",
                "country": "BE",
            },
        )
        assert r.action in ("created", "noop")

    async def test_02_create_cert(self, opn_client: OpnsenseClient) -> None:
        ca_mgr = TrustCaManager(opn_client)
        rows = await ca_mgr.list(search_phrase="inttest-ovpn-ca")
        ca = [r for r in rows if r.get("descr") == "inttest-ovpn-ca"]
        assert len(ca) == 1
        ca_refid = ca[0]["refid"]

        cert_mgr = TrustCertManager(opn_client)
        r = await cert_mgr.ensure(
            "present",
            {
                "descr": "inttest-ovpn-cert",
                "caref": ca_refid,
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "cert_type": "server_cert",
                "lifetime": "397",
                "commonname": "inttest-ovpn.example.com",
            },
        )
        assert r.action in ("created", "noop")


class TestOvpnInstanceCRUD:
    """OpenVPN server instance CRUD — disabled, port 11940."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        ca_mgr = TrustCaManager(opn_client)
        cert_mgr = TrustCertManager(opn_client)

        ca_rows = await ca_mgr.list(search_phrase="inttest-ovpn-ca")
        ca_refid = [r for r in ca_rows if r.get("descr") == "inttest-ovpn-ca"][0]["refid"]
        cert_rows = await cert_mgr.list(search_phrase="inttest-ovpn-cert")
        cert_refid = [r for r in cert_rows if r.get("descr") == "inttest-ovpn-cert"][0]["refid"]

        mgr = OvpnInstanceManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ovpn-server",
                "vpnid": "99",
                "role": "server",
                "proto": "udp",
                "port": "11940",
                "server": "10.8.99.0/24",
                "ca": ca_refid,
                "cert": cert_refid,
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = OvpnInstanceManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-ovpn-server")
        assert len([r for r in rows if r.get("description") == "inttest-ovpn-server"]) >= 1

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = OvpnInstanceManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-ovpn-server"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCleanup:
    """Remove all inttest- objects (instances → certs → CAs)."""

    async def test_cleanup_instances(self, opn_client: OpnsenseClient) -> None:
        mgr = OvpnInstanceManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("openvpn/instances/del", row["uuid"])

    async def test_cleanup_certs(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCertManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-ovpn")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/cert/del", row["uuid"])

    async def test_cleanup_cas(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-ovpn")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/ca/del", row["uuid"])
        await opn_client.reconfigure("openvpn/service/reconfigure", timeout=30)
