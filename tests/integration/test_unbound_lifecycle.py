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

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.ub_acl import UbAclManager
from opnsense.managers.ub_dot import UbDotManager
from opnsense.managers.ub_forward import UbForwardManager
from opnsense.managers.ub_host_override import UbHostOverrideManager

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
# 5. Cleanup
# =============================================================================


class TestCleanup:
    """Remove any leftover inttest- objects."""

    async def test_cleanup_host_overrides(self, opn_client: OpnsenseClient) -> None:
        mgr = UbHostOverrideManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("hostname", "")):
                await opn_client.delete(
                    "unbound/settings/delHostOverride", row["uuid"]
                )
        await opn_client.reconfigure("unbound/service/reconfigure", timeout=60)

    async def test_cleanup_forwards(self, opn_client: OpnsenseClient) -> None:
        mgr = UbForwardManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("domain", "")):
                await opn_client.delete(
                    "unbound/settings/delForward", row["uuid"]
                )

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
