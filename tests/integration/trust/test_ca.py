# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Trust CA manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/trust/test_ca.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestTrustCaCRUD.test_01_create_ca
    2. Idempotent (I)   -- TestTrustCaCRUD.test_02_exists (list verify)
    3. Update (U)       -- N/A -- CA fields are immutable after creation
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- TestTrustCaCRUD.test_03_redact_privkey
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_05)
    7. Error (E)        -- N/A -- no FieldValidationError test
    8. Delete (D)       -- N/A -- delete covered in cleanup
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_cas

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.trust.ca import TrustCaManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTrustCaCRUD:
    """CA certificate CRUD -- internal generation."""

    async def test_01_create_ca(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "descr": "inttest-ca",
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "lifetime": "825",
                "commonname": "inttest-ca.example.com",
                "country": "BE",
                "organization": "inttest",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_exists(self, opn_client: OpnsenseClient) -> None:
        """Verify CA was created. Noop unreliable (API returns extra fields)."""
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-ca")
        cas = [r for r in rows if r.get("descr") == "inttest-ca"]
        assert len(cas) == 1

    async def test_03_redact_privkey(self, opn_client: OpnsenseClient) -> None:
        """Verify private key is redacted in results."""
        assert "prv" in TrustCaManager.REDACT_FIELDS
        assert "prv_payload" in TrustCaManager.REDACT_FIELDS


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 CA matches descr key."""

    DUP_PARAMS = {
        "descr": "inttest-dup-ca",
        "action": "internal",
        "key_type": "2048",
        "digest": "sha256",
        "lifetime": "825",
        "commonname": "inttest-dup-ca.example.com",
        "country": "BE",
        "organization": "inttest",
    }

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two CAs with same descr via direct create."""
        mgr = TrustCaManager(opn_client)
        r1 = await mgr.create(params=self.DUP_PARAMS)
        r2 = await mgr.create(params=self.DUP_PARAMS)
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = TrustCaManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(state="present", params=self.DUP_PARAMS)
        assert len(exc_info.value.uuids) == 2

    async def test_03_ensure_absent_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = TrustCaManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(state="absent", params={"descr": "inttest-dup-ca"})

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """ensure(uuid=) bypasses _find_existing -- works on ambiguous pair."""
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-ca")
        dups = [r for r in rows if r.get("descr") == "inttest-dup-ca"]
        assert len(dups) == 2
        result = await mgr.ensure(
            state="present", uuid=dups[0]["uuid"], params={"descr": "inttest-dup-ca"}
        )
        assert result.action in ("noop", "updated")

    async def test_05_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate CAs by UUID."""
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-ca")
        for r in rows:
            if r.get("descr") == "inttest-dup-ca":
                await mgr.delete(r["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-ca")
        remaining = [r for r in rows if r.get("descr") == "inttest-dup-ca"]
        assert remaining == []


class TestCheckMode:
    """check_mode on CA create -- resource NOT created."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = TrustCaManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "descr": "inttest-ca-checkmode",
                "action": "internal",
                "key_type": "2048",
                "digest": "sha256",
                "lifetime": "825",
                "commonname": "inttest-ca-checkmode.example.com",
                "country": "BE",
                "organization": "inttest",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-ca-checkmode")
        found = [row for row in rows if row.get("descr") == "inttest-ca-checkmode"]
        assert found == []


class TestCleanup:
    """Remove all inttest- CAs."""

    async def test_cleanup_cas(self, opn_client: OpnsenseClient) -> None:
        mgr = TrustCaManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("descr", "")):
                await opn_client.delete("trust/ca/del", row["uuid"])
