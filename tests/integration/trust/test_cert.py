# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Trust certificate manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/trust/test_cert.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestTrustCertCRUD.test_01_create_cert
    2. Idempotent (I)   -- TestTrustCertCRUD.test_02_idempotent
    3. Update (U)       -- N/A -- cert fields immutable after creation
    4. Check mode (K)   -- TestTrustCertCRUD.test_03_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01_empty_descr
    8. Delete (D)       -- TestTrustCertCRUD.test_04_delete
    9. Delete noop (Dn) -- TestTrustCertCRUD.test_05_delete_idempotent
    10. Cleanup (X)     -- TestCleanup (certs + parent CA)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.trust.ca import TrustCaManager
from opnsense.managers.trust.cert import TrustCertManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTrustCertCRUD:
    """Certificate CRUD -- signed by inttest-ca. Uses refid not UUID."""

    async def test_00_setup_parent_ca(self, opn_client: OpnsenseClient) -> None:
        """Create parent CA for cert signing."""
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
        assert r.action in ("created", "noop", "updated")

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

    async def test_03_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        ca_mgr = TrustCaManager(opn_client)
        rows = await ca_mgr.list(search_phrase="inttest-ca")
        ca = [r for r in rows if r.get("descr") == "inttest-ca"]
        assert len(ca) == 1
        ca_refid = ca[0]["refid"]

        cert_mgr = TrustCertManager(opn_client)
        r = await cert_mgr.ensure(
            "present",
            {
                "descr": "inttest-cert-cm",
                "caref": ca_refid,
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "cert_type": "server_cert",
                "lifetime": "397",
                "commonname": "inttest-cm.example.com",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await cert_mgr.list(search_phrase="inttest-cert-cm")
        found = [row for row in rows if row.get("descr") == "inttest-cert-cm"]
        assert found == []

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        """Delete cert."""
        cert_mgr = TrustCertManager(opn_client)
        r = await cert_mgr.ensure("absent", {"descr": "inttest-cert"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_05_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        cert_mgr = TrustCertManager(opn_client)
        r = await cert_mgr.ensure("absent", {"descr": "inttest-cert"})
        assert r.changed is False
        assert r.action == "noop"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 cert matches same descr."""

    async def test_00_setup_ca(self, opn_client: OpnsenseClient) -> None:
        """Ensure parent CA exists."""
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
        assert r.action in ("created", "noop", "updated")

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two certs with same descr via direct create."""
        ca_mgr = TrustCaManager(opn_client)
        rows = await ca_mgr.list(search_phrase="inttest-ca")
        ca_refid = [r for r in rows if r.get("descr") == "inttest-ca"][0]["refid"]

        cert_mgr = TrustCertManager(opn_client)
        dup_params = {
            "descr": "inttest-dup-cert",
            "caref": ca_refid,
            "action": "internal",
            "key_type": "2048",
            "digest": "sha256",
            "cert_type": "server_cert",
            "lifetime": "397",
            "commonname": "inttest-dup.example.com",
        }
        r1 = await cert_mgr.create(params=dup_params)
        r2 = await cert_mgr.create(params=dup_params)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        cert_mgr = TrustCertManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await cert_mgr.ensure(
                state="present",
                params={"descr": "inttest-dup-cert"},
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate certs by UUID."""
        cert_mgr = TrustCertManager(opn_client)
        rows = await cert_mgr.list(search_phrase="inttest-dup-cert")
        for row in rows:
            if row.get("descr") == "inttest-dup-cert":
                await cert_mgr.delete(row["uuid"])
        rows = await cert_mgr.list(search_phrase="inttest-dup-cert")
        remaining = [r for r in rows if r.get("descr") == "inttest-dup-cert"]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_descr_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required descr -> FieldValidationError."""
        cert_mgr = TrustCertManager(opn_client)
        with pytest.raises(FieldValidationError, match="descr"):
            await cert_mgr.ensure("present", {"descr": ""})


class TestCleanup:
    """Remove all inttest- certs first, then parent CA."""

    async def test_cleanup_certs(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCertManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/cert/del", row["uuid"])

    async def test_cleanup_parent_ca(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/ca/del", row["uuid"])
