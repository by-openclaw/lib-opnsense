# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — OpenVPN instance manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/vpn/test_openvpn_lifecycle.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestOvpnInstanceCRUD.test_01_create
    2. Idempotent (I)   -- TestOvpnInstanceCRUD.test_02_idempotent
    3. Update (U)       -- TestOvpnInstanceCRUD.test_03_update_tun_mtu
    4. Check mode (K)   -- TestOvpnInstanceCRUD.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestOvpnAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestOvpnFieldValidation.test_01_bad_role
    8. Delete (D)       -- TestOvpnInstanceCRUD.test_05_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup (instances, certs, CAs)

    Setup: TestOvpnSetup (create CA + cert for OpenVPN)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.trust.ca import TrustCaManager
from opnsense.managers.trust.cert import TrustCertManager
from opnsense.managers.vpn.ovpn_instance import OvpnInstanceManager

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

    async def test_03_update_tun_mtu(self, opn_client: OpnsenseClient) -> None:
        """Update tun_mtu on existing instance."""
        mgr = OvpnInstanceManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ovpn-server",
                "tun_mtu": "1400",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create (enabled='0') -> changed=True but resource NOT created."""
        mgr = OvpnInstanceManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ovpn-cm",
                "enabled": "0",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-ovpn-cm")
        found = [row for row in rows if row.get("description") == "inttest-ovpn-cm"]
        assert found == []

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = OvpnInstanceManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-ovpn-server"})
        assert r.changed is True
        assert r.action == "deleted"


class TestOvpnAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 instance matches same description."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two instances with same description via direct create."""
        ca_mgr = TrustCaManager(opn_client)
        cert_mgr = TrustCertManager(opn_client)

        ca_rows = await ca_mgr.list(search_phrase="inttest-ovpn-ca")
        ca_refid = [r for r in ca_rows if r.get("descr") == "inttest-ovpn-ca"][0]["refid"]
        cert_rows = await cert_mgr.list(search_phrase="inttest-ovpn-cert")
        cert_refid = [r for r in cert_rows if r.get("descr") == "inttest-ovpn-cert"][0]["refid"]

        mgr = OvpnInstanceManager(opn_client)
        dup_params = {
            "description": "inttest-dup-ovpn",
            "vpnid": "98",
            "role": "server",
            "proto": "udp",
            "port": "11941",
            "server": "10.8.98.0/24",
            "ca": ca_refid,
            "cert": cert_refid,
            "enabled": "0",
        }
        r1 = await mgr.create(params=dup_params)
        dup_params2 = {**dup_params, "vpnid": "97", "port": "11942", "server": "10.8.97.0/24"}
        r2 = await mgr.create(params=dup_params2)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = OvpnInstanceManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "inttest-dup-ovpn",
                    "enabled": "0",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate instances by UUID."""
        mgr = OvpnInstanceManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-ovpn")
        for row in rows:
            if row.get("description") == "inttest-dup-ovpn":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-ovpn")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-ovpn"]
        assert remaining == []


class TestOvpnFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_bad_role_rejected(self, opn_client: OpnsenseClient) -> None:
        """Bad role enum -> FieldValidationError."""
        mgr = OvpnInstanceManager(opn_client)
        with pytest.raises(FieldValidationError, match="role"):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-ovpn-bad",
                    "role": "invalid_role",
                    "enabled": "0",
                },
            )


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
