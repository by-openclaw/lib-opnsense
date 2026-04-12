# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Plugin manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/services/test_plugin.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- N/A -- read-only plugin manager
    2. Idempotent (I)   -- N/A -- read-only
    3. Update (U)       -- N/A -- read-only
    4. Check mode (K)   -- N/A -- read-only
    5. Read/list (R)    -- test_01_list_installed, test_02_is_installed,
                           test_03_list_plugins
    6. Ambiguous (A)    -- N/A -- read-only
    7. Error (E)        -- N/A -- read-only
    8. Delete (D)       -- N/A -- read-only
    9. Delete noop (Dn) -- N/A -- read-only
    10. Cleanup (X)     -- N/A -- read-only, no resources created

Naming convention:
    Read-only operations -- no test objects created.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.plugin import PluginManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestPluginManager:
    """Plugin list and check operations."""

    async def test_01_list_installed(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        installed = await mgr.list_installed()
        assert isinstance(installed, list)
        assert len(installed) >= 1

    async def test_02_is_installed(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        # os-ddclient was installed earlier in this session
        result = await mgr.is_installed("os-ddclient")
        assert isinstance(result, bool)

    async def test_03_list_plugins(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        plugins = await mgr.list_plugins()
        assert len(plugins) > 0
        names = [p.get("name", "") for p in plugins]
        assert any(n.startswith("os-") for n in names)
