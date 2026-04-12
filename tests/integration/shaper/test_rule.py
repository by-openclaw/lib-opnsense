# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Traffic Shaper rule manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/shaper/test_rule.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestTsRuleCRUD.test_01_create_rule
    2. Idempotent (I)   -- N/A -- composite match keys include interface+proto
    3. Update (U)       -- TestTsRuleCRUD.test_02_update_direction
    4. Check mode (K)   -- TestTsRuleCRUD.test_03_check_mode_create
    5. Read/list (R)    -- covered by CRUD flow
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01_bad_proto
    8. Delete (D)       -- TestTsRuleCRUD.test_04_delete_rule
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup (rules + parent pipe)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.shaper.ts_pipe import TsPipeManager
from opnsense.managers.shaper.ts_rule import TsRuleManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTsRuleCRUD:
    """Rule CRUD -- requires target pipe UUID."""

    async def test_00_setup_parent_pipe(self, opn_client: OpnsenseClient) -> None:
        """Create parent pipe for rule target dependency."""
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

    async def test_02_update_direction(self, opn_client: OpnsenseClient) -> None:
        """Update direction field on existing rule."""
        pipe_mgr = TsPipeManager(opn_client)
        rows = await pipe_mgr.list(search_phrase="inttest-pipe-for-queue")
        pipe = [r for r in rows if "inttest-pipe-for-queue" in str(r.get("description", ""))]
        pipe_uuid = pipe[0]["uuid"]

        mgr = TsRuleManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-rule",
                "interface": "lan",
                "proto": "ip",
                "target": pipe_uuid,
                "direction": "in",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_03_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        pipe_mgr = TsPipeManager(opn_client)
        rows = await pipe_mgr.list(search_phrase="inttest-pipe-for-queue")
        pipe = [r for r in rows if "inttest-pipe-for-queue" in str(r.get("description", ""))]
        pipe_uuid = pipe[0]["uuid"]

        mgr = TsRuleManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-rule-cm",
                "interface": "lan",
                "proto": "udp",
                "target": pipe_uuid,
                "enabled": "0",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-rule-cm")
        found = [row for row in rows if row.get("description") == "inttest-rule-cm"]
        assert found == []

    async def test_04_delete_rule(self, opn_client: OpnsenseClient) -> None:
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


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 rule matches same composite keys."""

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
        """Create two rules with same description+interface+proto via direct create."""
        pipe_mgr = TsPipeManager(opn_client)
        rows = await pipe_mgr.list(search_phrase="inttest-pipe-for-queue")
        pipe = [r for r in rows if "inttest-pipe-for-queue" in str(r.get("description", ""))]
        pipe_uuid = pipe[0]["uuid"]

        mgr = TsRuleManager(opn_client)
        dup_params = {
            "description": "inttest-dup-rule",
            "interface": "lan",
            "proto": "ip",
            "target": pipe_uuid,
            "enabled": "0",
        }
        r1 = await mgr.create(params=dup_params)
        r2 = await mgr.create(params=dup_params)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = TsRuleManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "inttest-dup-rule",
                    "interface": "lan",
                    "proto": "ip",
                    "enabled": "0",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate rules by UUID."""
        mgr = TsRuleManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-rule")
        for row in rows:
            if row.get("description") == "inttest-dup-rule":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-rule")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-rule"]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_bad_proto_rejected(self, opn_client: OpnsenseClient) -> None:
        """Bad proto enum -> FieldValidationError."""
        mgr = TsRuleManager(opn_client)
        with pytest.raises(FieldValidationError, match="proto"):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-rule-bad",
                    "interface": "lan",
                    "proto": "invalid_proto",
                    "enabled": "0",
                },
            )


class TestCleanup:
    """Remove all inttest- TS rules and parent pipe."""

    async def test_cleanup_rules(self, opn_client: OpnsenseClient) -> None:
        mgr = TsRuleManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delRule", row["uuid"])

    async def test_cleanup_parent_pipe(self, opn_client: OpnsenseClient) -> None:
        mgr = TsPipeManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-pipe-for-queue")
        for row in rows:
            if "inttest-pipe-for-queue" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delPipe", row["uuid"])
        await opn_client.reconfigure("trafficshaper/service/reconfigure")
