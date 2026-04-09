# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — TS queue + rule managers on live OPNsense device.

Queue requires parent pipe UUID. Rule requires target pipe/queue UUID.
All objects disabled, inttest- prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.shaper.ts_pipe import TsPipeManager
from opnsense.managers.shaper.ts_queue import TsQueueManager
from opnsense.managers.shaper.ts_rule import TsRuleManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTsQueueCRUD:
    """Queue CRUD — requires parent pipe."""

    async def test_01_create_parent_pipe(self, opn_client: OpnsenseClient) -> None:
        mgr = TsPipeManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-pipe-for-queue",
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
                "enabled": "0",
            },
        )
        assert r.action in ("created", "noop")

    async def test_02_create_queue(self, opn_client: OpnsenseClient) -> None:
        pipe_mgr = TsPipeManager(opn_client)
        rows = await pipe_mgr.list(search_phrase="inttest-pipe-for-queue")
        pipe = [r for r in rows if "inttest-pipe-for-queue" in str(r.get("description", ""))]
        assert len(pipe) >= 1
        pipe_uuid = pipe[0]["uuid"]

        mgr = TsQueueManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-queue",
                "pipe": pipe_uuid,
                "weight": "50",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_03_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = TsQueueManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-queue",
                "weight": "50",
                "enabled": "0",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_04_delete_queue(self, opn_client: OpnsenseClient) -> None:
        mgr = TsQueueManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-queue"})
        assert r.changed is True
        assert r.action == "deleted"


class TestTsRuleCRUD:
    """Rule CRUD — requires target pipe UUID."""

    async def test_01_create_rule(self, opn_client: OpnsenseClient) -> None:
        pipe_mgr = TsPipeManager(opn_client)
        rows = await pipe_mgr.list(search_phrase="inttest-pipe-for-queue")
        pipe = [r for r in rows if "inttest-pipe-for-queue" in str(r.get("description", ""))]
        assert len(pipe) >= 1
        pipe_uuid = pipe[0]["uuid"]

        mgr = TsRuleManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-rule",
                "interface": "lan",
                "proto": "ip",
                "target": pipe_uuid,
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_delete_rule(self, opn_client: OpnsenseClient) -> None:
        mgr = TsRuleManager(opn_client)
        r = await mgr.ensure(
            "absent",
            {
                "description": "inttest-rule",
                "interface": "lan",
                "proto": "ip",
            },
        )
        assert r.changed is True
        assert r.action == "deleted"


class TestCleanup:
    """Remove all inttest- TS objects (queues/rules first, then pipes)."""

    async def test_cleanup_queues(self, opn_client: OpnsenseClient) -> None:
        mgr = TsQueueManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delQueue", row["uuid"])

    async def test_cleanup_rules(self, opn_client: OpnsenseClient) -> None:
        mgr = TsRuleManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delRule", row["uuid"])

    async def test_cleanup_pipes(self, opn_client: OpnsenseClient) -> None:
        mgr = TsPipeManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delPipe", row["uuid"])
        await opn_client.reconfigure("trafficshaper/service/reconfigure")
