# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — FW NPTv6 (NAT66) on live OPNsense device.

NPTv6 translates IPv6 prefixes — used for multi-homed IPv6 networks.
All rules created disabled with ULA prefixes (fd00::/64), inttest- prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.firewall.npt import FwNptManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

NPT_PARAMS = {
    "source_net": "fd00:1::/64",
    "destination_net": "fd00:2::/64",
    "interface": "lan",
    "enabled": "0",
    "description": "inttest-nptv6",
}


class TestNptCRUD:
    """NPTv6 CRUD — disabled rules, ULA prefixes."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        r = await mgr.ensure("present", NPT_PARAMS)
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        r = await mgr.ensure("present", NPT_PARAMS)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        updated = {**NPT_PARAMS, "description": "inttest-nptv6-updated"}
        r = await mgr.ensure("present", updated)
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"source_net": "fd00:1::/64", "destination_net": "fd00:2::/64"},
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"source_net": "fd00:1::/64", "destination_net": "fd00:2::/64"},
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {"source_net": "fd00:1::/64", "destination_net": "fd00:2::/64"},
        )
        assert r.changed is False
        assert r.action == "noop"


class TestCleanup:
    """Remove any leftover inttest- NPTv6 rules."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("firewall/npt/delRule", row["uuid"])
        await opn_client.post("firewall/npt/apply")
