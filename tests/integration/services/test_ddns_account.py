# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- DynDNS account manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/services/test_ddns_account.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestDdnsCRUD.test_01_create
    2. Idempotent (I)   -- TestDdnsCRUD.test_02_idempotent
    3. Update (U)       -- TestDdnsCRUD.test_03_update_hostname
    4. Check mode (K)   -- TestDdnsCRUD.test_05_check_mode_create
    5. Read/list (R)    -- TestDdnsCRUD.test_04_redact_password
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01_empty_description
    8. Delete (D)       -- TestDdnsCRUD.test_06_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.services.ddns_account import DdnsAccountManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDdnsCRUD:
    """DynDNS account CRUD -- Cloudflare, disabled."""

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

    async def test_03_update_hostname(self, opn_client: OpnsenseClient) -> None:
        """Update hostnames field -> changed."""
        mgr = DdnsAccountManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ddns",
                "service": "cloudflare",
                "username": "inttest@example.com",
                "password": "inttest-api-token",
                "hostnames": "inttest-updated.example.com",
                "zone": "example.com",
                "checkip": "web_cloudflare",
                "interface": "wan",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_redact_password(self, opn_client: OpnsenseClient) -> None:
        assert "password" in DdnsAccountManager.REDACT_FIELDS

    async def test_05_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create (enabled='0') -> changed=True but resource NOT created."""
        mgr = DdnsAccountManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ddns-cm",
                "service": "cloudflare",
                "username": "cm@example.com",
                "password": "cm-token",
                "hostnames": "cm.example.com",
                "zone": "example.com",
                "checkip": "web_cloudflare",
                "interface": "wan",
                "enabled": "0",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-ddns-cm")
        found = [row for row in rows if row.get("description") == "inttest-ddns-cm"]
        assert found == []

    async def test_06_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DdnsAccountManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-ddns"})
        assert r.changed is True
        assert r.action == "deleted"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 account matches same description."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two accounts with same description via direct create."""
        mgr = DdnsAccountManager(opn_client)
        dup_params = {
            "description": "inttest-dup-ddns",
            "service": "cloudflare",
            "username": "dup@example.com",
            "password": "dup-token",
            "hostnames": "dup.example.com",
            "zone": "example.com",
            "checkip": "web_cloudflare",
            "interface": "wan",
            "enabled": "0",
        }
        r1 = await mgr.create(params=dup_params)
        r2 = await mgr.create(params=dup_params)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = DdnsAccountManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "inttest-dup-ddns",
                    "service": "cloudflare",
                    "hostnames": "dup.example.com",
                    "checkip": "web_cloudflare",
                    "enabled": "0",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate accounts by UUID."""
        mgr = DdnsAccountManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-ddns")
        for row in rows:
            if row.get("description") == "inttest-dup-ddns":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-ddns")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-ddns"]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_description_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required description -> FieldValidationError."""
        mgr = DdnsAccountManager(opn_client)
        with pytest.raises(FieldValidationError, match="description"):
            await mgr.ensure(
                "present",
                {
                    "description": "",
                    "service": "cloudflare",
                    "hostnames": "test.example.com",
                    "checkip": "web_cloudflare",
                    "enabled": "0",
                },
            )


class TestCleanup:
    """Remove all inttest- DynDNS accounts."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DdnsAccountManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("dyndns/accounts/delItem", row["uuid"])
        await opn_client.reconfigure("dyndns/service/reconfigure", timeout=30)
