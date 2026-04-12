# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- firewall alias CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_alias.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestAliasCRUD.test_01 (host), test_04 (net),
                           test_09 (port), test_12 (url), test_15 (urltable),
                           test_18 (mac)
    2. Idempotent (I)   -- TestAliasCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestAliasCRUD.test_03_update_content
    4. Check mode (K)   -- TestAliasCRUD.test_06_check_mode_delete
    5. Read/list (R)    -- TestAliasCRUD.test_05_list_contains_test_aliases
    6. Ambiguous (A)    -- N/A -- OPNsense enforces alias name uniqueness
    7. Error (E)        -- TestErrorHandling.test_01_empty_name_rejected
    8. Delete (D)       -- TestAliasCRUD.test_07/08/11/14/17/20
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_aliases

Naming convention:
    All test objects use prefix 'inttest_alias_' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.firewall.alias import FwAliasManager

# Test object names
ALIAS_NAME = "inttest_alias_host"
ALIAS_NAME_NET = "inttest_alias_net"
ALIAS_NAME_PORT = "inttest_alias_port"
ALIAS_NAME_URL = "inttest_alias_url"
ALIAS_NAME_URLTABLE = "inttest_alias_urltbl"
ALIAS_NAME_MAC = "inttest_alias_mac"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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


class TestErrorHandling:
    """Error handling -- validate that bad input raises FieldValidationError."""

    async def test_01_empty_name_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required name caught client-side -- FieldValidationError."""
        mgr = FwAliasManager(opn_client)
        with pytest.raises(FieldValidationError, match="name"):
            await mgr.ensure(
                state="present",
                params={"name": "", "type": "host", "content": "10.11.1.1"},
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test aliases."""

    async def test_99_cleanup_aliases(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest_alias_ aliases (excludes infra inttest_admin_*)."""
        mgr = FwAliasManager(opn_client)
        rows = await mgr.list(search_phrase="inttest_alias")
        for row in rows:
            if row.get("name", "").startswith("inttest_alias"):
                await mgr.delete(row["uuid"])
