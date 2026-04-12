# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Traffic Shaper queue manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/shaper/test_queue.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestTsQueueCRUD.test_01_create_queue
    2. Idempotent (I)   -- TestTsQueueCRUD.test_02_idempotent
    3. Update (U)       -- TestTsQueueCRUD.test_03_update_weight
    4. Check mode (K)   -- TestTsQueueCRUD.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01_empty_description
    8. Delete (D)       -- TestTsQueueCRUD.test_05_delete_queue
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup (queues + parent pipe)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.shaper.ts_pipe import TsPipeManager
from opnsense.managers.shaper.ts_queue import TsQueueManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTsQueueCRUD:
    """Queue CRUD -- requires parent pipe."""

    async def test_00_setup_parent_pipe(self, opn_client: OpnsenseClient) -> None:
        """Create parent pipe for queue dependency."""
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

    async def test_01_create_queue(self, opn_client: OpnsenseClient) -> None:
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

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
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

    async def test_03_update_weight(self, opn_client: OpnsenseClient) -> None:
        """Update weight field on existing queue."""
        mgr = TsQueueManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-queue",
                "weight": "75",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = TsQueueManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-queue-cm",
                "weight": "30",
                "enabled": "0",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-queue-cm")
        found = [row for row in rows if row.get("description") == "inttest-queue-cm"]
        assert found == []

    async def test_05_delete_queue(self, opn_client: OpnsenseClient) -> None:
        mgr = TsQueueManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-queue"})
        assert r.changed is True
        assert r.action == "deleted"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 queue matches same description."""

    async def test_00_setup_parent_pipe(self, opn_client: OpnsenseClient) -> None:
        """Ensure parent pipe exists."""
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

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two queues with same description via direct create."""
        pipe_mgr = TsPipeManager(opn_client)
        rows = await pipe_mgr.list(search_phrase="inttest-pipe-for-queue")
        pipe = [r for r in rows if "inttest-pipe-for-queue" in str(r.get("description", ""))]
        pipe_uuid = pipe[0]["uuid"]

        mgr = TsQueueManager(opn_client)
        r1 = await mgr.create(
            params={
                "description": "inttest-dup-queue",
                "pipe": pipe_uuid,
                "weight": "50",
                "enabled": "0",
            }
        )
        r2 = await mgr.create(
            params={
                "description": "inttest-dup-queue",
                "pipe": pipe_uuid,
                "weight": "60",
                "enabled": "0",
            }
        )
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = TsQueueManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "inttest-dup-queue",
                    "weight": "50",
                    "enabled": "0",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate queues by UUID."""
        mgr = TsQueueManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-queue")
        for row in rows:
            if row.get("description") == "inttest-dup-queue":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-queue")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-queue"]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_description_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required description -> FieldValidationError."""
        mgr = TsQueueManager(opn_client)
        with pytest.raises(FieldValidationError, match="description"):
            await mgr.ensure(
                "present",
                {"description": "", "weight": "50", "enabled": "0"},
            )


class TestCleanup:
    """Remove all inttest- TS queues and parent pipe."""

    async def test_cleanup_queues(self, opn_client: OpnsenseClient) -> None:
        mgr = TsQueueManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delQueue", row["uuid"])

    async def test_cleanup_parent_pipe(self, opn_client: OpnsenseClient) -> None:
        mgr = TsPipeManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-pipe-for-queue")
        for row in rows:
            if "inttest-pipe-for-queue" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delPipe", row["uuid"])
        await opn_client.reconfigure("trafficshaper/service/reconfigure")
