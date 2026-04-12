# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — NPTv6 (NAT66) prefix translation against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/firewall/test_npt_lifecycle.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestNptCRUD.test_01_create
    2. Idempotent (I)   -- TestNptCRUD.test_02_idempotent
    3. Update (U)       -- TestNptCRUD.test_03_update
    4. Check mode (K)   -- TestNptCRUD.test_04_check_mode_delete
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestErrorHandling.test_01_empty_source_net
    8. Delete (D)       -- TestNptCRUD.test_05_delete
    9. Delete noop (Dn) -- TestNptCRUD.test_06_delete_idempotent
    10. Cleanup (X)     -- TestCleanup.test_cleanup

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
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


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 NPT rule matches same source_net+destination_net."""

    DUP_PARAMS = {
        "source_net": "fd00:a::/64",
        "destination_net": "fd00:b::/64",
        "interface": "lan",
        "enabled": "0",
        "description": "inttest-dup-npt",
    }

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two NPT rules with same source_net+destination_net via direct create."""
        mgr = FwNptManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = FwNptManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate NPT rules by UUID."""
        mgr = FwNptManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-npt")
        for row in rows:
            if row.get("description") == "inttest-dup-npt":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-npt")
        remaining = [r for r in rows if r.get("description") == "inttest-dup-npt"]
        assert remaining == []


class TestErrorHandling:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_source_net_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty source_net -> FieldValidationError."""
        mgr = FwNptManager(opn_client)
        with pytest.raises(FieldValidationError, match="source_net"):
            await mgr.ensure(
                "present",
                {
                    "source_net": "",
                    "destination_net": "fd00:2::/64",
                    "interface": "lan",
                    "enabled": "0",
                    "description": "inttest-npt-bad",
                },
            )


class TestCleanup:
    """Remove any leftover inttest- NPTv6 rules."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = FwNptManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("firewall/npt/delRule", row["uuid"])
        await opn_client.post("firewall/npt/apply")
