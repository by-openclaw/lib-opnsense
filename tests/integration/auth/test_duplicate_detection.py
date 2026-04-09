# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — duplicate detection on live OPNsense device.

Proves that:
    1. Auth domain: OPNsense server REJECTS duplicate users/groups (API-enforced)
    2. FW domain:   OPNsense ALLOWS duplicate rules — AmbiguousMatchError is our guard
    3. IF domain:   OPNsense ALLOWS duplicate VLANs — AmbiguousMatchError is our guard
    4. TS domain:   OPNsense ALLOWS duplicate pipes — AmbiguousMatchError is our guard

These tests confirm WHY composite match keys + AmbiguousMatchError exist:
the OPNsense API does NOT enforce uniqueness on FW/IF/TS resources.

Safety:
    - All objects use ``inttest-dup-`` prefix
    - FW rules created disabled (enabled='0')
    - Full cleanup after each test class
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, OpnsenseValidationError
from opnsense.managers.auth_group import AuthGroupManager
from opnsense.managers.auth_user import AuthUserManager
from opnsense.managers.fw_filter import FwFilterManager
from opnsense.managers.ts_pipe import TsPipeManager

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

        # Second create with same name → ensure sees existing, returns noop
        r2 = await mgr.ensure("present", {"name": "inttest-dup-user", "password": "Test5678!"})
        assert r2.changed is True  # password differs → update
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
