# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — duplicate detection across domains against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/auth/test_duplicate_detection.py -v

Test flow (cross-cutting: duplicate detection across domains):
    Not a standard per-manager CRUD lifecycle. Tests duplicate handling
    across auth, firewall, and traffic shaper domains.
    1. Create (C)       -- N/A -- cross-cutting duplicate detection
    2. Idempotent (I)   -- N/A
    3. Update (U)       -- N/A
    4. Check mode (K)   -- N/A
    5. Read/list (R)    -- N/A
    6. Ambiguous (A)    -- TestAuthDuplicateRejection (API rejects),
                           TestFwDuplicateDetection (AmbiguousMatchError),
                           TestTsDuplicateDetection (AmbiguousMatchError)
    7. Error (E)        -- covered by ambiguous tests above
    8. Delete (D)       -- N/A
    9. Delete noop (Dn) -- N/A
    10. Cleanup (X)     -- per-class test_99_cleanup methods

Naming convention:
    All test objects use prefix 'inttest-dup-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, OpnsenseValidationError
from opnsense.managers.auth.group import AuthGroupManager
from opnsense.managers.auth.user import AuthUserManager
from opnsense.managers.firewall.filter import FwFilterManager
from opnsense.managers.shaper.ts_pipe import TsPipeManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# 1. Auth — Server-side duplicate rejection (API enforces uniqueness)
# =============================================================================


class TestAuthDuplicateRejection:
    """OPNsense API rejects duplicate users and groups — no AmbiguousMatch needed."""

    async def test_01_duplicate_user_rejected_by_api(self, opn_client: OpnsenseClient) -> None:
        """Creating the same username twice → server returns validation error."""
        mgr = AuthUserManager(opn_client)

        # First create succeeds
        r1 = await mgr.ensure("present", {"name": "inttest-dup-user", "password": "Test1234!"})
        assert r1.changed is True
        assert r1.action == "created"

        # Second ensure with DIFFERENT password → bcrypt verify detects mismatch → update
        # Search endpoint returns $2y$ hash, diff engine uses bcrypt.checkpw()
        r2 = await mgr.ensure("present", {"name": "inttest-dup-user", "password": "Test5678!"})
        assert r2.changed is True
        assert r2.action == "updated"

    async def test_02_duplicate_user_direct_api_rejected(self, opn_client: OpnsenseClient) -> None:
        """Bypassing ensure() — raw API rejects duplicate username."""
        with pytest.raises(OpnsenseValidationError, match="already exist"):
            await opn_client.create(
                "auth/user/add",
                "user",
                {"name": "inttest-dup-user", "password": "Direct1234!"},
            )

    async def test_03_duplicate_group_rejected_by_api(self, opn_client: OpnsenseClient) -> None:
        """Creating the same group name twice → server returns validation error."""
        mgr = AuthGroupManager(opn_client)

        r1 = await mgr.ensure("present", {"name": "inttest-dup-group"})
        assert r1.changed is True

        # ensure() finds existing → noop (same params)
        r2 = await mgr.ensure("present", {"name": "inttest-dup-group"})
        assert r2.changed is False
        assert r2.action == "noop"

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest-dup- auth objects."""
        user_mgr = AuthUserManager(opn_client)
        group_mgr = AuthGroupManager(opn_client)

        await user_mgr.ensure("absent", {"name": "inttest-dup-user"})
        await group_mgr.ensure("absent", {"name": "inttest-dup-group"})


# =============================================================================
# 2. FW Filter — API allows duplicates, AmbiguousMatch is our guard
# =============================================================================


class TestFwDuplicateDetection:
    """OPNsense ALLOWS duplicate FW rules — AmbiguousMatchError catches them."""

    async def test_01_create_rule(self, opn_client: OpnsenseClient) -> None:
        """Create a filter rule via ensure()."""
        mgr = FwFilterManager(opn_client)
        r1 = await mgr.ensure(
            "present",
            {
                "description": "inttest-dup-rule",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "enabled": "0",
            },
        )
        assert r1.changed is True
        assert r1.action == "created"

    async def test_02_duplicate_via_raw_api_succeeds(self, opn_client: OpnsenseClient) -> None:
        """Bypassing ensure() — raw API happily creates a duplicate rule."""
        uuid = await opn_client.create(
            "firewall/filter/addRule",
            "rule",
            {
                "description": "inttest-dup-rule",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "enabled": "0",
            },
        )
        assert uuid  # Created with new UUID — duplicate exists now

    async def test_03_ensure_detects_ambiguity(self, opn_client: OpnsenseClient) -> None:
        """ensure() on duplicated rule → AmbiguousMatchError with both UUIDs."""
        mgr = FwFilterManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-dup-rule",
                    "action": "pass",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "enabled": "0",
                },
            )
        assert len(exc_info.value.uuids) == 2
        assert "inttest-dup-rule" in str(exc_info.value.match_keys.get("description", ""))

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """uuid= param bypasses search and targets a specific duplicate."""
        mgr = FwFilterManager(opn_client)

        # List to find both UUIDs
        rows = await mgr.list(search_phrase="inttest-dup-rule")
        dupes = [r for r in rows if r.get("description") == "inttest-dup-rule"]
        assert len(dupes) == 2

        # Target first one by UUID — no AmbiguousMatchError
        r = await mgr.ensure(
            "absent",
            {
                "description": "inttest-dup-rule",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
            uuid=dupes[0]["uuid"],
        )
        assert r.changed is True
        assert r.action == "deleted"

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest-dup- filter rules."""
        mgr = FwFilterManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-rule")
        for row in rows:
            if "inttest-dup" in str(row.get("description", "")):
                await opn_client.delete("firewall/filter/delRule", row["uuid"])
        await opn_client.post("firewall/filter/apply")


# =============================================================================
# 3. Traffic Shaper — API allows duplicates, AmbiguousMatch is our guard
# =============================================================================


class TestTsDuplicateDetection:
    """OPNsense ALLOWS duplicate pipes — AmbiguousMatchError catches them."""

    async def test_01_create_pipe(self, opn_client: OpnsenseClient) -> None:
        """Create a pipe via ensure()."""
        mgr = TsPipeManager(opn_client)
        r1 = await mgr.ensure(
            "present",
            {
                "description": "inttest-dup-pipe",
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
                "enabled": "0",
            },
        )
        assert r1.changed is True
        assert r1.action == "created"

    async def test_02_duplicate_via_raw_api_succeeds(self, opn_client: OpnsenseClient) -> None:
        """Raw API creates duplicate pipe without error."""
        uuid = await opn_client.create(
            "trafficshaper/settings/addPipe",
            "pipe",
            {
                "description": "inttest-dup-pipe",
                "bandwidth": "10",
                "bandwidthMetric": "Mbit",
                "enabled": "0",
            },
        )
        assert uuid

    async def test_03_ensure_detects_ambiguity(self, opn_client: OpnsenseClient) -> None:
        """ensure() on duplicated pipe → AmbiguousMatchError."""
        mgr = TsPipeManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                {
                    "description": "inttest-dup-pipe",
                    "bandwidth": "10",
                    "bandwidthMetric": "Mbit",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_99_cleanup(self, opn_client: OpnsenseClient) -> None:
        """Remove all inttest-dup- pipes."""
        mgr = TsPipeManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-pipe")
        for row in rows:
            if "inttest-dup" in str(row.get("description", "")):
                await opn_client.delete("trafficshaper/settings/delPipe", row["uuid"])
        await opn_client.post("trafficshaper/service/reconfigure")
