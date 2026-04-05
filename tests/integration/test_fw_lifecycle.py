# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests for firewall managers — alias, filter, D-NAT, source NAT.

Requires a live OPNsense 26.1+ device.
All test objects use the ``inttest-`` prefix to avoid collision with production config.
Tests run in order within each class (test_01_, test_02_, ...) and clean up after.

Environment variables:
    OPN_HOST, OPN_KEY, OPN_SECRET, OPN_PORT, OPN_VERIFY_SSL

Safety:
    - Only creates/modifies/deletes objects with ``inttest-`` prefix
    - Final cleanup class removes all test objects
    - Safe to run against a PoC device (see CLAUDE.md boundary rules)
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.fw_alias import FwAliasManager
from opnsense.managers.fw_dnat import FwDnatManager
from opnsense.managers.fw_filter import FwFilterManager
from opnsense.managers.fw_source_nat import FwSourceNatManager

# Test object names — all prefixed with inttest-
ALIAS_NAME = "inttest_alias_host"
ALIAS_NAME_NET = "inttest_alias_net"
FILTER_DESC = "inttest-filter-allow-https"
DNAT_DESC = "inttest-dnat-forward-http"
SNAT_DESC = "inttest-snat-masquerade"


@pytest.mark.integration
@pytest.mark.asyncio
class TestAliasCRUD:
    """CRUD lifecycle for firewall aliases."""

    async def test_01_create_host_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a host alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME,
                "type": "host",
                "content": "10.6.225.99",
                "description": "Integration test host alias",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME,
                "type": "host",
                "content": "10.6.225.99",
                "description": "Integration test host alias",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_content(self, opn_client: OpnsenseClient) -> None:
        """Update alias content -> changed."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME,
                "type": "host",
                "content": "10.6.225.100",
                "description": "Integration test host alias",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_create_network_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a network alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_NET,
                "type": "network",
                "content": "10.6.225.0/24",
                "description": "Integration test network alias",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_05_list_contains_test_aliases(self, opn_client: OpnsenseClient) -> None:
        """Search confirms both test aliases exist."""
        mgr = FwAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        names = [r["name"] for r in rows]
        assert ALIAS_NAME in names
        assert ALIAS_NAME_NET in names

    async def test_06_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        """check_mode delete -> changed=True but alias still exists."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME}, check_mode=True)
        assert result.changed is True
        assert result.action == "deleted"

        # Alias should still exist
        rows = await mgr.list(search_phrase=ALIAS_NAME)
        assert any(r["name"] == ALIAS_NAME for r in rows)

    async def test_07_delete_host_alias(self, opn_client: OpnsenseClient) -> None:
        """Delete host alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_08_delete_network_alias(self, opn_client: OpnsenseClient) -> None:
        """Delete network alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME_NET})
        assert result.changed is True
        assert result.action == "deleted"


@pytest.mark.integration
@pytest.mark.asyncio
class TestFilterCRUD:
    """CRUD lifecycle for firewall filter rules."""

    async def test_01_create_filter_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a filter rule allowing HTTPS."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": FILTER_DESC,
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "ipprotocol": "inet",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "1",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": FILTER_DESC,
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "ipprotocol": "inet",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "1",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_action_to_block(self, opn_client: OpnsenseClient) -> None:
        """Update rule action from pass to block -> changed."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": FILTER_DESC,
                "action": "block",
                "interface": "lan",
                "direction": "in",
                "ipprotocol": "inet",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "1",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_list_contains_test_rule(self, opn_client: OpnsenseClient) -> None:
        """Search confirms test rule exists."""
        mgr = FwFilterManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        descriptions = [r.get("description", "") for r in rows]
        assert FILTER_DESC in descriptions

    async def test_05_delete_filter_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the filter rule."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(state="absent", params={"description": FILTER_DESC})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(state="absent", params={"description": FILTER_DESC})
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.integration
@pytest.mark.asyncio
class TestDnatCRUD:
    """CRUD lifecycle for D-NAT (port forward) rules. Requires OPNsense >= 26.1."""

    async def test_01_create_dnat_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a D-NAT port forward rule."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.6.225.99",
                "local-port": "80",
                "disabled": "0",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.6.225.99",
                "local-port": "80",
                "disabled": "0",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_target(self, opn_client: OpnsenseClient) -> None:
        """Update D-NAT target -> changed."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.6.225.100",
                "local-port": "80",
                "disabled": "0",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_dnat_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the D-NAT rule."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(state="absent", params={"descr": DNAT_DESC})
        assert result.changed is True
        assert result.action == "deleted"


@pytest.mark.integration
@pytest.mark.asyncio
class TestSourceNatCRUD:
    """CRUD lifecycle for source NAT rules."""

    async def test_01_create_snat_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a source NAT masquerade rule."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
                "enabled": "1",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Second ensure with same params -> noop."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
                "enabled": "1",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_delete_snat_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the source NAT rule."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(state="absent", params={"description": SNAT_DESC})
        assert result.changed is True
        assert result.action == "deleted"


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """Error handling tests against live device."""

    async def test_01_invalid_state_raises(self, opn_client: OpnsenseClient) -> None:
        """Invalid state raises ValueError."""
        mgr = FwAliasManager(opn_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"name": "test"})

    async def test_02_check_mode_no_side_effects(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> no resource created on device."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "inttest-should-not-exist", "action": "pass"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"

        # Verify it was NOT actually created
        rows = await mgr.list(search_phrase="inttest-should-not-exist")
        assert not any(r.get("description") == "inttest-should-not-exist" for r in rows)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCleanup:
    """Final cleanup — remove any leftover test objects."""

    async def test_99_cleanup_aliases(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest_ aliases."""
        mgr = FwAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("name", "").startswith("inttest"):
                await mgr.delete(row["uuid"])

    async def test_99_cleanup_filter_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- filter rules."""
        mgr = FwFilterManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])

    async def test_99_cleanup_dnat_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- D-NAT rules."""
        mgr = FwDnatManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("descr", "").startswith("inttest"):
                await mgr.delete(row["uuid"])

    async def test_99_cleanup_snat_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- source NAT rules."""
        mgr = FwSourceNatManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
