# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- ACME account manager against a live OPNsense device.

Requirements:
    - Live OPNsense (os-acme-client plugin) via OPN_HOST/OPN_KEY/OPN_SECRET
    - Run with: pytest tests/integration/acme/test_accounts.py -v

Safety: uses the 'inttest-' prefix and the Let's Encrypt **staging** CA. Never
calls ``register`` (which would contact the live CA). Cleans up everything.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.acme.accounts import AcmeAccountManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

NAME = "inttest-acme-account"


class TestAcmeAccountCRUD:
    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeAccountManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": NAME,
                "email": "inttest@example.com",
                "ca": "letsencrypt_test",
                "description": "inttest",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_exists(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeAccountManager(opn_client)
        rows = await mgr.list(search_phrase=NAME)
        assert [row for row in rows if row.get("name") == NAME]

    async def test_03_redact_defined(self) -> None:
        assert "key" in AcmeAccountManager.REDACT_FIELDS
        assert "eab_hmac" in AcmeAccountManager.REDACT_FIELDS

    async def test_04_verbs_present(self) -> None:
        assert hasattr(AcmeAccountManager, "register")
        assert hasattr(AcmeAccountManager, "status")

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeAccountManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("acmeclient/accounts/del", row["uuid"])
        rows = await mgr.list(search_phrase=NAME)
        assert [row for row in rows if row.get("name") == NAME] == []
