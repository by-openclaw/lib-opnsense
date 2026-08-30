# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- ACME certificate manager against a live OPNsense device.

Creates a certificate referencing a throwaway account + validation, verifies it
lists, then cleans up everything. Safety: 'inttest-' prefix; **never** calls
``sign`` (no external CA traffic). The lifecycle verbs are asserted as present.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.acme.accounts import AcmeAccountManager
from opnsense.managers.acme.certificates import AcmeCertificateManager
from opnsense.managers.acme.validations import AcmeValidationManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

CERT = "inttest-acme-cert.example.com"
ACCT = "inttest-cert-account"
VALID = "inttest-cert-validation"


class TestAcmeCertificateCRUD:
    async def test_01_create_refs_and_cert(self, opn_client: OpnsenseClient) -> None:
        accounts = AcmeAccountManager(opn_client)
        validations = AcmeValidationManager(opn_client)
        certs = AcmeCertificateManager(opn_client)

        ra = await accounts.ensure(
            "present", {"name": ACCT, "email": "inttest@example.com", "ca": "letsencrypt_test"}
        )
        rv = await validations.ensure(
            "present",
            {"name": VALID, "method": "dns01", "dns_service": "dns_cf", "dns_cf_token": "dummy"},
        )
        # resolve uuids (ensure may noop if a prior run left them; re-list)
        acct_rows = await accounts.list(search_phrase=ACCT)
        val_rows = await validations.list(search_phrase=VALID)
        acct_uuid = ra.uuid or next(r["uuid"] for r in acct_rows if r["name"] == ACCT)
        val_uuid = rv.uuid or next(r["uuid"] for r in val_rows if r["name"] == VALID)

        r = await certs.ensure(
            "present",
            {
                "name": CERT,
                "account": acct_uuid,
                "validationMethod": val_uuid,
                "keyLength": "key_ec256",
                "description": "inttest",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_exists(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeCertificateManager(opn_client)
        rows = await mgr.list(search_phrase=CERT)
        assert [row for row in rows if row.get("name") == CERT]

    async def test_03_lifecycle_verbs_present(self) -> None:
        for verb in ("sign", "revoke", "remove_key", "automation", "import_"):
            assert hasattr(AcmeCertificateManager, verb)

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        # Order: cert → validation → account (cert references the others).
        for endpoint, mgr_cls, phrase in (
            ("acmeclient/certificates/del", AcmeCertificateManager, "inttest"),
            ("acmeclient/validations/del", AcmeValidationManager, "inttest"),
            ("acmeclient/accounts/del", AcmeAccountManager, "inttest"),
        ):
            mgr = mgr_cls(opn_client)
            rows = await mgr.list(search_phrase=phrase)
            for row in rows:
                if "inttest" in str(row.get("name", "")):
                    await opn_client.delete(endpoint, row["uuid"])
        certs = AcmeCertificateManager(opn_client)
        rows = await certs.list(search_phrase=CERT)
        assert [row for row in rows if row.get("name") == CERT] == []
