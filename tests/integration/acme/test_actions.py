# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- ACME action manager against a live OPNsense device.

Safety: 'inttest-' prefix; the action is created but never attached to a cert,
so it never runs. Cleans up everything.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.acme.actions import AcmeActionManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

NAME = "inttest-acme-action"


class TestAcmeActionCRUD:
    async def test_01_create_restart_gui(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeActionManager(opn_client)
        r = await mgr.ensure(
            "present",
            {"name": NAME, "type": "configd_restart_gui", "description": "inttest"},
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_exists(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeActionManager(opn_client)
        rows = await mgr.list(search_phrase=NAME)
        assert [row for row in rows if row.get("name") == NAME]

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeActionManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("acmeclient/actions/del", row["uuid"])
        rows = await mgr.list(search_phrase=NAME)
        assert [row for row in rows if row.get("name") == NAME] == []
