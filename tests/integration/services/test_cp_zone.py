# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Captive Portal zone manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/services/test_cp_zone.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestCpZoneCRUD.test_01_create
    2. Idempotent (I)   -- TestCpZoneCRUD.test_02_idempotent
    3. Update (U)       -- TestCpZoneCRUD.test_03_update
    4. Check mode (K)   -- TestCpZoneCRUD.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01_empty_description
    8. Delete (D)       -- TestCpZoneCRUD.test_05_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_zones

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.services.cp_zone import CpZoneManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestCpZoneCRUD:
    """Captive Portal zone -- created disabled on LAN."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "300",
                "hardtimeout": "3600",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "300",
                "hardtimeout": "3600",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "600",
                "hardtimeout": "7200",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create (enabled='0') -> changed=True but resource NOT created."""
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-portal-cm",
                "interfaces": "lan",
                "enabled": "0",
                "idletimeout": "300",
                "hardtimeout": "3600",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-portal-cm")
        found = [row for row in rows if row.get("description") == "inttest-portal-cm"]
        assert found == []

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-portal"})
        assert r.changed is True
        assert r.action == "deleted"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 zone matches same description."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two zones with same description via direct create."""
        mgr = CpZoneManager(opn_client)
        dup_params = {
            "description": "inttest-dup-portal",
            "interfaces": "lan",
            "enabled": "0",
        }
        r1 = await mgr.create(params=dup_params)
        r2 = await mgr.create(params=dup_params)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = CpZoneManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "inttest-dup-portal",
                    "interfaces": "lan",
                    "enabled": "0",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate zones by UUID."""
        mgr = CpZoneManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-portal")
        for row in rows:
            if row.get("description") == "inttest-dup-portal":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-portal")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-portal"]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_description_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required description -> FieldValidationError."""
        mgr = CpZoneManager(opn_client)
        with pytest.raises(FieldValidationError, match="description"):
            await mgr.ensure(
                "present",
                {"description": "", "interfaces": "lan", "enabled": "0"},
            )


class TestCleanup:
    """Remove all inttest- captive portal zones."""

    async def test_cleanup_zones(self, opn_client: OpnsenseClient) -> None:
        mgr = CpZoneManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("captiveportal/settings/delZone", row["uuid"])
