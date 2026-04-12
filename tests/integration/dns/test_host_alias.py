# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — UbHostAliasManager lifecycle against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dns/test_host_alias.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestHostAliasCRUD.test_02_create_alias
    2. Idempotent (I)   -- N/A -- 26.1.5 missing setHostAlias
    3. Update (U)       -- N/A -- 26.1.5 returns 404 on setHostAlias
    4. Check mode (K)   -- N/A -- cannot verify without delHostAlias
    5. Read/list (R)    -- TestHostAliasCRUD.test_03_list_alias
    6. Ambiguous (A)    -- N/A -- cannot test without delete for cleanup
    7. Error (E)        -- TestErrorHandling.test_04_empty_hostname_raises
    8. Delete (D)       -- N/A -- 26.1.5 returns 404 on delHostAlias
    9. Delete noop (Dn) -- N/A -- delete not available
    10. Cleanup (X)     -- TestCleanup (aliases + parent overrides)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import contextlib

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.dns.ub_host_alias import UbHostAliasManager
from opnsense.managers.dns.ub_host_override import UbHostOverrideManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestHostAliasCRUD:
    """Host alias lifecycle. Requires a parent host override.

    LIMITATION: OPNsense 26.1.5 does not expose setHostAlias or delHostAlias.
    Only create + read tested. Cleanup uses raw client delete on parent override.
    """

    async def test_01_create_parent_host(self, opn_client: OpnsenseClient) -> None:
        """Create parent host override for alias testing."""
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "hostname": "inttest-alias-parent",
                "domain": "lab.test",
                "server": "10.11.2.20",
                "rr": "A",
                "description": "inttest-alias-parent",
            },
        )
        assert r.action in ("created", "noop")

    async def test_02_create_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a host alias pointing to the parent override."""
        # Find parent UUID
        override_mgr = UbHostOverrideManager(opn_client)
        rows = await override_mgr.list(search_phrase="inttest-alias-parent")
        parent = [r for r in rows if r.get("hostname") == "inttest-alias-parent"]
        assert len(parent) == 1, "Parent host override must exist"
        parent_uuid = parent[0]["uuid"]

        mgr = UbHostAliasManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "host": parent_uuid,
                "hostname": "inttest-web-alias",
                "domain": "lab.test",
                "description": "inttest-host-alias",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_03_list_alias(self, opn_client: OpnsenseClient) -> None:
        """Verify alias appears in search results."""
        mgr = UbHostAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-web-alias")
        aliases = [r for r in rows if r.get("hostname") == "inttest-web-alias"]
        assert len(aliases) >= 1


class TestErrorHandling:
    """Field validation error tests."""

    async def test_04_empty_hostname_raises(self, opn_client: OpnsenseClient) -> None:
        """Empty hostname (required field) -> FieldValidationError."""
        mgr = UbHostAliasManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {
                    "hostname": "",
                    "domain": "lab.test",
                    "host": "00000000-0000-0000-0000-000000000000",
                    "description": "inttest-bad-alias",
                },
            )


class TestCleanup:
    """Remove any leftover inttest- host aliases and their parent overrides."""

    async def test_cleanup_host_aliases(self, opn_client: OpnsenseClient) -> None:
        """Remove host aliases first (before parent overrides)."""
        mgr = UbHostAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("hostname", "")):
                # delHostAlias may 404 on 26.1.5
                with contextlib.suppress(Exception):
                    await opn_client.delete("unbound/settings/delHostAlias", row["uuid"])

    async def test_cleanup_parent_overrides(self, opn_client: OpnsenseClient) -> None:
        """Remove parent host overrides created for alias testing."""
        mgr = UbHostOverrideManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-alias-parent")
        for row in rows:
            if row.get("hostname") == "inttest-alias-parent":
                await opn_client.delete("unbound/settings/delHostOverride", row["uuid"])
        await opn_client.reconfigure("unbound/service/reconfigure", timeout=60)
