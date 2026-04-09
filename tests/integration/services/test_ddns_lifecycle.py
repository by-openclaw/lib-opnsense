# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — DynDNS account manager on live OPNsense device.

Built-in DynDNS on 26.1 (not os-ddclient plugin). Supports Cloudflare.
All accounts disabled with inttest- prefix and example.com domain.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.ddns_account import DdnsAccountManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDdnsCRUD:
    """DynDNS account CRUD — Cloudflare, disabled."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DdnsAccountManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ddns",
                "service": "cloudflare",
                "username": "inttest@example.com",
                "password": "inttest-api-token",
                "hostnames": "inttest.example.com",
                "zone": "example.com",
                "checkip": "web_cloudflare",
                "interface": "wan",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DdnsAccountManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ddns",
                "service": "cloudflare",
                "username": "inttest@example.com",
                "password": "inttest-api-token",
                "hostnames": "inttest.example.com",
                "zone": "example.com",
                "checkip": "web_cloudflare",
                "interface": "wan",
                "enabled": "0",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_redact_password(self, opn_client: OpnsenseClient) -> None:
        assert "password" in DdnsAccountManager.REDACT_FIELDS

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DdnsAccountManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-ddns"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCleanup:
    """Remove all inttest- DynDNS accounts."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DdnsAccountManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("dyndns/accounts/delItem", row["uuid"])
        await opn_client.reconfigure("dyndns/service/reconfigure", timeout=30)
