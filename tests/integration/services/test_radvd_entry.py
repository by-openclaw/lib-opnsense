# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — radvd entry manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/services/test_radvd_entry.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       — TestRadvdEntryCRUD.test_01_create
    2. Idempotent (I)   — TestRadvdEntryCRUD.test_02_idempotent
    3. Update (U)       — TestRadvdEntryCRUD.test_03_update
    4. Check mode (K)   — TestRadvdEntryCRUD.test_04_check_mode_create
    5. Read/list (R)    — covered by idempotent (test_02)
    6. Ambiguous (A)    — TestAmbiguousMatch
    7. Error (E)        — TestFieldValidation
    8. Delete (D)       — TestRadvdEntryCRUD.test_05_delete
    9. Delete noop (Dn) — TestRadvdEntryCRUD.test_06_delete_noop
    10. Cleanup (X)     — TestCleanup.test_cleanup

Safety boundaries (read carefully before running):
    - Every test entry is created with ``enabled='0'``. The radvd daemon
      will NOT broadcast Router Advertisements for disabled entries even
      if it is started elsewhere.
    - Test interface is ``lan`` (OOB management). Even in the unlikely
      event of accidental enabling, the OOB segment has no IPv6 clients
      that would be affected by a stray RA.
    - The radvd service itself is NOT started by this suite; only entries
      are CRUDed. Reconfigure calls hit a daemon that may be in ``unknown``
      state — that is expected and non-disruptive.
    - The cleanup test deletes every entry whose interface is ``lan`` or
      ``opt12`` (the test slots) — it will NOT touch entries on other
      interfaces, so production entries on the same FW remain untouched.
"""

from __future__ import annotations

import contextlib

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.services.radvd_entry import RadvdEntryManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Test interfaces — see safety note in module docstring
INTTEST_IFACE_PRIMARY = "lan"
INTTEST_IFACE_DUP = "opt12"
INTTEST_IFACES = (INTTEST_IFACE_PRIMARY, INTTEST_IFACE_DUP)


class TestRadvdEntryCRUD:
    """Radvd entry CRUD — entries kept disabled, restricted to test interfaces."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE_PRIMARY,
                "enabled": "0",
                "mode": "stateless",
            },
        )
        assert r.changed is True
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE_PRIMARY,
                "enabled": "0",
                "mode": "stateless",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": INTTEST_IFACE_PRIMARY,
                "enabled": "0",
                "mode": "managed",  # changed from 'stateless'
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "interface": "opt11",  # cctv — no test entry created here normally
                "enabled": "0",
                "mode": "stateless",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        rows = await mgr.list()
        assert not any(row.get("interface") == "opt11" for row in rows), (
            "check_mode must not create resources"
        )

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.ensure("absent", {"interface": INTTEST_IFACE_PRIMARY})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_06_delete_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.ensure("absent", {"interface": INTTEST_IFACE_PRIMARY})
        assert r.changed is False
        assert r.action == "noop"


class TestUniquenessEnforced:
    """OPNsense enforces unique ``interface`` on radvd entries server-side.

    Attempting to create a second entry on the same interface raises
    ``OpnsenseValidationError`` rather than producing duplicates that would
    trigger ``AmbiguousMatchError``. Ambiguity is still tested at the unit
    level (mocked search returns two matches) — see
    ``tests/unit/managers/services/test_radvd_entry.py::TestAmbiguousMatch``.
    """

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        r = await mgr.create(
            params={
                "interface": INTTEST_IFACE_DUP,
                "enabled": "0",
                "mode": "stateless",
            }
        )
        assert r.uuid

    async def test_02_second_create_rejected_by_server(self, opn_client: OpnsenseClient) -> None:
        from opnsense.exceptions import OpnsenseValidationError

        mgr = RadvdEntryManager(opn_client)
        with pytest.raises(OpnsenseValidationError, match="interface"):
            await mgr.create(
                params={
                    "interface": INTTEST_IFACE_DUP,
                    "enabled": "0",
                    "mode": "stateless",
                }
            )

    async def test_03_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("interface") == INTTEST_IFACE_DUP:
                await mgr.delete(row["uuid"])
        rows = await mgr.list()
        remaining = [r for r in rows if r.get("interface") == INTTEST_IFACE_DUP]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_missing_interface(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        with pytest.raises(FieldValidationError, match="interface"):
            await mgr.ensure("present", {"mode": "managed", "enabled": "0"})

    async def test_02_invalid_mode_enum(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        with pytest.raises(FieldValidationError, match="mode"):
            await mgr.ensure(
                "present",
                {
                    "interface": INTTEST_IFACE_PRIMARY,
                    "mode": "bogus-mode",
                    "enabled": "0",
                },
            )


class TestCleanup:
    """Remove any test entries that may remain on the test interfaces."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdEntryManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("interface") in INTTEST_IFACES:
                await opn_client.delete("radvd/settings/delEntry", row["uuid"])
        with contextlib.suppress(Exception):
            # radvd may not be running on a fresh FW — cleanup must not fail on apply
            await opn_client.reconfigure("radvd/service/reconfigure", timeout=15)
