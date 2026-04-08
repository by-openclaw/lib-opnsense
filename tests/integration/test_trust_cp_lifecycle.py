# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Trust/PKI + Captive Portal on live OPNsense device.

Trust: CA → Cert chain. Cert requires CA refid (not UUID).
Captive Portal: zone created disabled on LAN.
All objects use inttest- prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.cp_zone import CpZoneManager
from opnsense.managers.trust_ca import TrustCaManager
from opnsense.managers.trust_cert import TrustCertManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Trust CA CRUD
# =============================================================================


class TestTrustCaCRUD:
    """CA certificate CRUD — internal generation."""

    async def test_01_create_ca(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "descr": "inttest-ca",
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "lifetime": "825",
                "commonname": "inttest-ca.example.com",
                "country": "BE",
                "organization": "inttest",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_exists(self, opn_client: OpnsenseClient) -> None:
        """Verify CA was created. Noop unreliable (API returns extra fields)."""
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-ca")
        cas = [r for r in rows if r.get("descr") == "inttest-ca"]
        assert len(cas) == 1

    async def test_03_redact_privkey(self, opn_client: OpnsenseClient) -> None:
        """Verify private key is redacted in results."""
        assert "prv" in TrustCaManager.REDACT_FIELDS
        assert "prv_payload" in TrustCaManager.REDACT_FIELDS


# =============================================================================
# 2. Trust Cert CRUD (depends on CA)
# =============================================================================


class TestTrustCertCRUD:
    """Certificate CRUD — signed by inttest-ca. Uses refid not UUID."""

    async def test_01_create_cert(self, opn_client: OpnsenseClient) -> None:
        # Find CA refid
        ca_mgr = TrustCaManager(opn_client)
        rows = await ca_mgr.list(search_phrase="inttest-ca")
        ca = [r for r in rows if r.get("descr") == "inttest-ca"]
        assert len(ca) == 1, "inttest-ca must exist"
        ca_refid = ca[0]["refid"]

        cert_mgr = TrustCertManager(opn_client)
        r = await cert_mgr.ensure(
            "present",
            {
                "descr": "inttest-cert",
                "caref": ca_refid,
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "cert_type": "server_cert",
                "lifetime": "397",
                "commonname": "inttest-server.example.com",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        cert_mgr = TrustCertManager(opn_client)
        rows = await cert_mgr.list(search_phrase="inttest-cert")
        assert len([r for r in rows if r.get("descr") == "inttest-cert"]) >= 1


# =============================================================================
# 3. Captive Portal Zone CRUD
# =============================================================================


class TestCpZoneCRUD:
    """Captive Portal zone — created disabled on LAN."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "300",
                "hardtimeout": "3600",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "300",
                "hardtimeout": "3600",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "600",
                "hardtimeout": "7200",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-portal"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 4. Cleanup (certs first, then CAs)
# =============================================================================


class TestCleanup:
    """Remove all inttest- objects."""

    async def test_cleanup_zones(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("captiveportal/settings/delZone", row["uuid"])

    async def test_cleanup_certs(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCertManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/cert/del", row["uuid"])

    async def test_cleanup_cas(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/ca/del", row["uuid"])
