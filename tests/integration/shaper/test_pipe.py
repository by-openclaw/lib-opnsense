# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- traffic shaper pipe CRUD lifecycle.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/shaper/test_pipe.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestPipeCRUD.test_01_create_pipe
    2. Idempotent (I)   -- TestPipeCRUD.test_02_idempotent_noop
    3. Update (U)       -- TestPipeCRUD.test_03_update_enabled
    4. Check mode (K)   -- TestPipeCRUD.test_06_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- N/A -- tested in test_duplicate_detection
    7. Error (E)        -- TestFieldValidation.test_01_bandwidth_zero
    8. Delete (D)       -- TestPipeCRUD.test_04_delete_pipe
    9. Delete noop (Dn) -- TestPipeCRUD.test_05_delete_noop
    10. Cleanup (X)     -- TestCleanup.test_99_cleanup_pipes

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.shaper.ts_pipe import TsPipeManager

PIPE_DESC = "inttest-pipe"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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

    async def test_06_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = TsPipeManager(opn_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "inttest-pipe-cm",
                "bandwidth": "5",
                "bandwidthMetric": "Mbit",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-pipe-cm")
        found = [r for r in rows if r.get("description") == "inttest-pipe-cm"]
        assert found == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_bandwidth_zero_rejected(self, opn_client: OpnsenseClient) -> None:
        """bandwidth=0 -> FieldValidationError (int min=1)."""
        mgr = TsPipeManager(opn_client)
        with pytest.raises(FieldValidationError, match="bandwidth"):
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-pipe-bad",
                    "bandwidth": "0",
                    "bandwidthMetric": "Mbit",
                },
            )


class TestCleanup:
    """Final cleanup -- remove any leftover test pipes."""

    async def test_99_cleanup_pipes(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest- pipes."""
        mgr = TsPipeManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if row.get("description", "").startswith("inttest"):
                await mgr.delete(row["uuid"])
