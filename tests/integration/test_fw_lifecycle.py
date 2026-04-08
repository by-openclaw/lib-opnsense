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
from opnsense.managers.fw_category import FwCategoryManager
from opnsense.managers.fw_dnat import FwDnatManager
from opnsense.managers.fw_filter import FwFilterManager
from opnsense.managers.fw_group import FwGroupManager
from opnsense.managers.fw_one_to_one import FwOneToOneManager
from opnsense.managers.fw_source_nat import FwSourceNatManager
from opnsense.managers.ts_pipe import TsPipeManager

# Test object names — all prefixed with inttest-
ALIAS_NAME = "inttest_alias_host"
ALIAS_NAME_NET = "inttest_alias_net"
ALIAS_NAME_PORT = "inttest_alias_port"
ALIAS_NAME_URL = "inttest_alias_url"
ALIAS_NAME_URLTABLE = "inttest_alias_urltbl"
ALIAS_NAME_MAC = "inttest_alias_mac"
FILTER_DESC = "inttest-filter-allow-https"
DNAT_DESC = "inttest-dnat-forward-http"
ONETOONE_DESC = "inttest-1to1-binat"
CATEGORY_NAME = "inttest-category"
GROUP_IFNAME = "inttest_grp"
PIPE_DESC = "inttest-pipe"
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
                "content": "10.11.1.99",
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
                "content": "10.11.1.99",
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
                "content": "10.11.1.100",
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
                "content": "10.11.1.0/24",
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

    # -- Port alias --

    async def test_09_create_port_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a port alias with a range."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_PORT,
                "type": "port",
                "content": "8080:8090",
                "description": "Integration test port alias",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_10_port_alias_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Port alias noop."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_PORT,
                "type": "port",
                "content": "8080:8090",
                "description": "Integration test port alias",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_11_delete_port_alias(self, opn_client: OpnsenseClient) -> None:
        """Delete port alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME_PORT})
        assert result.changed is True
        assert result.action == "deleted"

    # -- URL alias --

    async def test_12_create_url_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a URL alias (static URL content, not auto-refreshed)."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_URL,
                "type": "url",
                "content": "https://example.com/blocklist.txt",
                "description": "Integration test URL alias",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_13_url_alias_idempotent(self, opn_client: OpnsenseClient) -> None:
        """URL alias noop."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_URL,
                "type": "url",
                "content": "https://example.com/blocklist.txt",
                "description": "Integration test URL alias",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_14_delete_url_alias(self, opn_client: OpnsenseClient) -> None:
        """Delete URL alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME_URL})
        assert result.changed is True
        assert result.action == "deleted"

    # -- URL table alias (auto-refresh) --

    async def test_15_create_urltable_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a URL table alias with refresh interval."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_URLTABLE,
                "type": "urltable",
                "content": "https://example.com/iplist.txt",
                "updatefreq": "1",
                "description": "Integration test URL table alias",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_16_urltable_alias_idempotent(self, opn_client: OpnsenseClient) -> None:
        """URL table alias noop."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_URLTABLE,
                "type": "urltable",
                "content": "https://example.com/iplist.txt",
                "updatefreq": "1",
                "description": "Integration test URL table alias",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_17_delete_urltable_alias(self, opn_client: OpnsenseClient) -> None:
        """Delete URL table alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME_URLTABLE})
        assert result.changed is True
        assert result.action == "deleted"

    # -- MAC alias --

    async def test_18_create_mac_alias(self, opn_client: OpnsenseClient) -> None:
        """Create a MAC address alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_MAC,
                "type": "mac",
                "content": "00:11:22:33:44:55",
                "description": "Integration test MAC alias",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_19_mac_alias_idempotent(self, opn_client: OpnsenseClient) -> None:
        """MAC alias noop."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": ALIAS_NAME_MAC,
                "type": "mac",
                "content": "00:11:22:33:44:55",
                "description": "Integration test MAC alias",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_20_delete_mac_alias(self, opn_client: OpnsenseClient) -> None:
        """Delete MAC alias."""
        mgr = FwAliasManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": ALIAS_NAME_MAC})
        assert result.changed is True
        assert result.action == "deleted"

    # -- List all test aliases cleaned --

    async def test_21_verify_all_cleaned(self, opn_client: OpnsenseClient) -> None:
        """Verify no inttest_alias_ aliases remain (excludes infra aliases)."""
        mgr = FwAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest_alias")
        test_aliases = [r for r in rows if r.get("name", "").startswith("inttest_alias")]
        assert test_aliases == [], f"Leftover aliases: {[a['name'] for a in test_aliases]}"


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
                "enabled": "0",
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
                "enabled": "0",
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
                "enabled": "0",
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
        result = await mgr.ensure(
            state="absent",
            params={
                "description": FILTER_DESC,
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwFilterManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": FILTER_DESC,
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        )
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.integration
@pytest.mark.asyncio
class TestDnatCRUD:
    """CRUD lifecycle for D-NAT (port forward) rules. Requires OPNsense >= 26.1.

    SAFETY: ALL rules created with disabled=1. D-NAT apply on WAN crashed
    the FW on 2026-04-05 and 2026-04-07. Disabled rules are safe — apply
    runs but pf does not load the rule into the ruleset.
    """

    async def test_01_create_dnat_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a D-NAT port forward rule (disabled)."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.11.2.10",
                "local-port": "80",
                "disabled": "1",
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
                "target": "10.11.2.10",
                "local-port": "80",
                "disabled": "1",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_local_port(self, opn_client: OpnsenseClient) -> None:
        """Update D-NAT local-port -> changed (still disabled).

        Note: ``target`` is a composite match key and cannot be used for
        drift/update tests.  We update ``local-port`` instead.
        """
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "protocol": "tcp",
                "target": "10.11.2.10",
                "local-port": "8080",
                "disabled": "1",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_dnat_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the D-NAT rule."""
        mgr = FwDnatManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "descr": DNAT_DESC,
                "interface": "wan",
                "target": "10.11.2.10",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"


@pytest.mark.integration
@pytest.mark.asyncio
class TestSourceNatCRUD:
    """CRUD lifecycle for source NAT rules.

    SAFETY: ALL rules created with enabled=0. SNAT apply on WAN can
    disrupt routing — same risk as D-NAT. Disabled rules are safe.
    """

    async def test_01_create_snat_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a source NAT masquerade rule (disabled)."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "ipprotocol": "inet",
                "source_net": "10.11.3.0/24",
                "target": "wanip",
                "enabled": "0",
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
                "source_net": "10.11.3.0/24",
                "target": "wanip",
                "enabled": "0",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_delete_snat_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the source NAT rule."""
        mgr = FwSourceNatManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": SNAT_DESC,
                "interface": "wan",
                "source_net": "10.11.3.0/24",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"


@pytest.mark.integration
@pytest.mark.asyncio
class TestOneToOneCRUD:
    """CRUD lifecycle for 1:1 NAT (BINAT) rules.

    SAFETY: ALL rules created with disabled=1.
    """

    async def test_01_create_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a 1:1 NAT rule (disabled)."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "type": "binat",
                "external": "10.11.1.200",
                "source_net": "10.11.2.10/32",
                "disabled": "1",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "type": "binat",
                "external": "10.11.1.200",
                "source_net": "10.11.2.10/32",
                "disabled": "1",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_delete_rule(self, opn_client: OpnsenseClient) -> None:
        """Delete the 1:1 NAT rule."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "source_net": "10.11.2.10/32",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_04_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwOneToOneManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": ONETOONE_DESC,
                "interface": "wan",
                "source_net": "10.11.2.10/32",
            },
        )
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.integration
@pytest.mark.asyncio
class TestCategoryCRUD:
    """CRUD lifecycle for firewall categories. No apply needed."""

    async def test_01_create_category(self, opn_client: OpnsenseClient) -> None:
        """Create a category."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": CATEGORY_NAME, "color": "ff0000"},
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": CATEGORY_NAME, "color": "ff0000"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_color(self, opn_client: OpnsenseClient) -> None:
        """Update color -> changed."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"name": CATEGORY_NAME, "color": "00ff00"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_category(self, opn_client: OpnsenseClient) -> None:
        """Delete category."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": CATEGORY_NAME})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_05_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwCategoryManager(opn_client)
        result = await mgr.ensure(state="absent", params={"name": CATEGORY_NAME})
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.integration
@pytest.mark.asyncio
class TestGroupCRUD:
    """CRUD lifecycle for firewall interface groups. No apply needed."""

    async def test_01_create_group(self, opn_client: OpnsenseClient) -> None:
        """Create an interface group."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": GROUP_IFNAME, "members": "lan", "descr": "Integration test group"},
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": GROUP_IFNAME, "members": "lan", "descr": "Integration test group"},
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_description(self, opn_client: OpnsenseClient) -> None:
        """Update description -> changed."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": GROUP_IFNAME, "members": "lan", "descr": "Updated test group"},
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_group(self, opn_client: OpnsenseClient) -> None:
        """Delete interface group."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"ifname": GROUP_IFNAME})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_05_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = FwGroupManager(opn_client)
        result = await mgr.ensure(state="absent", params={"ifname": GROUP_IFNAME})
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.integration
@pytest.mark.asyncio
class TestPipeCRUD:
    """CRUD lifecycle for traffic shaper pipes."""

    async def test_01_create_pipe(self, opn_client: OpnsenseClient) -> None:
        """Create a pipe."""
        mgr = TsPipeManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": PIPE_DESC,
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
            },
        )
        assert result.changed is True
        assert result.action in ("created", "updated")

    async def test_02_idempotent_noop(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = TsPipeManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": PIPE_DESC,
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_03_update_enabled(self, opn_client: OpnsenseClient) -> None:
        """Update enabled flag -> changed.

        Note: ``bandwidth`` and ``bandwidthMetric`` are composite match keys
        and cannot be used for drift/update tests.  We toggle ``enabled``
        instead.
        """
        mgr = TsPipeManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": PIPE_DESC,
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
                "enabled": "0",
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_04_delete_pipe(self, opn_client: OpnsenseClient) -> None:
        """Delete pipe."""
        mgr = TsPipeManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": PIPE_DESC,
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
            },
        )
        assert result.changed is True
        assert result.action == "deleted"

    async def test_05_delete_noop(self, opn_client: OpnsenseClient) -> None:
        """Delete again -> noop."""
        mgr = TsPipeManager(opn_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": PIPE_DESC,
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
            },
        )
        assert result.changed is False
        assert result.action == "noop"


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
        """Remove all inttest_alias_ aliases (excludes infra inttest_admin_*)."""
        mgr = FwAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest_alias")
        for row in rows:
            if row.get("name", "").startswith("inttest_alias"):
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

    async def test_99_cleanup_one_to_one_rules(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- 1:1 NAT rules."""
        mgr = FwOneToOneManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])

    async def test_99_cleanup_categories(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- categories."""
        mgr = FwCategoryManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("name", "").startswith("inttest"):
                await mgr.delete(row["uuid"])

    async def test_99_cleanup_groups(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest_ interface groups."""
        mgr = FwGroupManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("ifname", "").startswith("inttest"):
                await mgr.delete(row["uuid"])

    async def test_99_cleanup_pipes(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- pipes."""
        mgr = TsPipeManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
