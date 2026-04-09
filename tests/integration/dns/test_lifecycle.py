# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Unbound DNS managers on live OPNsense device.

Requires a live OPNsense 26.1+ device with Unbound enabled.
All test objects use ``inttest-`` prefix.

Test flow (ordered per class):
    1. Host Override CRUD — create, noop, update, delete, check_mode, idempotency
    2. Forward CRUD — create, noop, delete
    3. ACL CRUD — create, noop, update, delete
    4. DoT CRUD — create (disabled), noop, delete
    5. Cleanup — remove all inttest- objects

Safety:
    - All DoT entries created with enabled='0'
    - All objects use inttest- prefix or .test domain
    - Full cleanup after each class
"""

from __future__ import annotations

import contextlib

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.dns.ub_acl import UbAclManager
from opnsense.managers.dns.ub_diagnostics import UbDiagnosticsManager
from opnsense.managers.dns.ub_dot import UbDotManager
from opnsense.managers.dns.ub_forward import UbForwardManager
from opnsense.managers.dns.ub_host_alias import UbHostAliasManager
from opnsense.managers.dns.ub_host_override import UbHostOverrideManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# -- Test data -----------------------------------------------------------------

HOST_OVERRIDE = {
    "hostname": "inttest-web",
    "domain": "lab.test",
    "server": "10.11.2.10",
    "rr": "A",
    "enabled": "1",
    "description": "inttest-host-override",
}

FORWARD = {
    "domain": "inttest.test",
    "server": "10.11.1.53",
    "type": "forward",
    "enabled": "1",
    "description": "inttest-forward",
}

ACL = {
    "name": "inttest-acl-testzone",
    "action": "allow",
    "networks": "10.11.0.0/16",
    "enabled": "1",
    "description": "inttest-acl",
}

DOT = {
    "server": "10.99.99.99",
    "port": "853",
    "type": "dot",
    "verify": "inttest.example.com",
    "enabled": "0",
    "description": "inttest-dot",
}


# =============================================================================
# 1. Host Override CRUD
# =============================================================================


class TestHostOverrideCRUD:
    """CRUD lifecycle for Unbound host overrides."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure("present", HOST_OVERRIDE)
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure("present", HOST_OVERRIDE)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        updated = {**HOST_OVERRIDE, "description": "inttest-host-override-updated"}
        r = await mgr.ensure("present", updated)
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"hostname": "inttest-web", "domain": "lab.test", "server": "10.11.2.10"},
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "deleted"
        # Still exists after check_mode
        r2 = await mgr.ensure("present", HOST_OVERRIDE)
        assert r2.action in ("noop", "updated")

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"hostname": "inttest-web", "domain": "lab.test", "server": "10.11.2.10"},
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"hostname": "inttest-web", "domain": "lab.test", "server": "10.11.2.10"},
        )
        assert r.changed is False
        assert r.action == "noop"


# =============================================================================
# 2. Forward CRUD
# =============================================================================


class TestForwardCRUD:
    """CRUD lifecycle for Unbound DNS forwarding."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        r = await mgr.ensure("present", FORWARD)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        r = await mgr.ensure("present", FORWARD)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        r = await mgr.ensure("absent", {"domain": "inttest.test", "server": "10.11.1.53"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 3. ACL CRUD
# =============================================================================


class TestAclCRUD:
    """CRUD lifecycle for Unbound access control lists."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        r = await mgr.ensure("present", ACL)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        r = await mgr.ensure("present", ACL)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        updated = {**ACL, "description": "inttest-acl-updated"}
        r = await mgr.ensure("present", updated)
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-acl-testzone"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 4. DoT CRUD (created disabled)
# =============================================================================


class TestDotCRUD:
    """CRUD lifecycle for Unbound DNS-over-TLS. Created disabled."""

    async def test_01_create_disabled(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        r = await mgr.ensure("present", DOT)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        r = await mgr.ensure("present", DOT)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        r = await mgr.ensure("absent", {"server": "10.99.99.99", "port": "853"})
        assert r.changed is True
        assert r.action == "deleted"


# =============================================================================
# 5. Host Alias (create + read only — set/del return 404 on 26.1.5)
# =============================================================================


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


# =============================================================================
# 6. Diagnostics + DNSBL (read-only)
# =============================================================================


class TestDiagnostics:
    """Read-only diagnostics — stats and DNSBL config."""

    async def test_01_get_stats(self, opn_client: OpnsenseClient) -> None:
        """Get resolver statistics — must return status=ok."""
        diag = UbDiagnosticsManager(opn_client)
        stats = await diag.get_stats()
        assert stats.get("status") == "ok"
        assert "data" in stats

    async def test_02_get_dnsbl(self, opn_client: OpnsenseClient) -> None:
        """Get DNSBL config — read-only on 26.1.5."""
        diag = UbDiagnosticsManager(opn_client)
        dnsbl = await diag.get_dnsbl()
        assert "enabled" in dnsbl

    async def test_03_list_dnsbl(self, opn_client: OpnsenseClient) -> None:
        """List DNSBL entries via search."""
        diag = UbDiagnosticsManager(opn_client)
        rows = await diag.list_dnsbl()
        assert isinstance(rows, list)


# =============================================================================
# 7. Cleanup
# =============================================================================


class TestCleanup:
    """Remove any leftover inttest- objects."""

    async def test_cleanup_host_aliases(self, opn_client: OpnsenseClient) -> None:
        """Remove host aliases first (before parent overrides)."""
        mgr = UbHostAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("hostname", "")):
                # delHostAlias may 404 on 26.1.5
                with contextlib.suppress(Exception):
                    await opn_client.delete("unbound/settings/delHostAlias", row["uuid"])

    async def test_cleanup_host_overrides(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("hostname", "")):
                await opn_client.delete("unbound/settings/delHostOverride", row["uuid"])
        await opn_client.reconfigure("unbound/service/reconfigure", timeout=60)

    async def test_cleanup_forwards(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("domain", "")):
                await opn_client.delete("unbound/settings/delForward", row["uuid"])

    async def test_cleanup_acls(self, opn_client: OpnsenseClient) -> None:
        mgr = UbAclManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("unbound/settings/delAcl", row["uuid"])

    async def test_cleanup_dots(self, opn_client: OpnsenseClient) -> None:
        mgr = UbDotManager(opn_client)
        rows = await mgr.list(search_phrase="10.99.99.99")
        for row in rows:
            await opn_client.delete("unbound/settings/delDot", row["uuid"])
