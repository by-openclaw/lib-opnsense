# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- ACME validation manager against a live OPNsense device.

Safety: 'inttest-' prefix, dummy Cloudflare token (never used — no cert is
signed). Cleans up everything.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.acme.validations import AcmeValidationManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

NAME = "inttest-acme-validation"


class TestAcmeValidationCRUD:
    async def test_01_create_cloudflare_dns01(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeValidationManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": NAME,
                "method": "dns01",
                "dns_service": "dns_cf",
                "dns_cf_token": "inttest-dummy-token",
                "description": "inttest",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_exists(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeValidationManager(opn_client)
        rows = await mgr.list(search_phrase=NAME)
        assert [row for row in rows if row.get("name") == NAME]

    async def test_03_redact_defined(self) -> None:
        assert "dns_cf_token" in AcmeValidationManager.REDACT_FIELDS

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeValidationManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("acmeclient/validations/del", row["uuid"])
        rows = await mgr.list(search_phrase=NAME)
        assert [row for row in rows if row.get("name") == NAME] == []
