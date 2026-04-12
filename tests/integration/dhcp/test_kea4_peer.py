# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- Kea DHCPv4 peer manager against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/dhcp/test_kea4_peer.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestKea4PeerCRUD.test_01_create
    2. Idempotent (I)   -- TestKea4PeerCRUD.test_02_idempotent
    3. Update (U)       -- TestKea4PeerCRUD.test_03_update_url
    4. Check mode (K)   -- TestKea4PeerCRUD.test_04_check_mode_create
    5. Read/list (R)    -- covered by idempotent (test_02)
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_03)
    7. Error (E)        -- TestFieldValidation.test_01 + test_02
    8. Delete (D)       -- TestKea4PeerCRUD.test_05_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup.test_cleanup_peers

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError, FieldValidationError
from opnsense.managers.dhcp.kea4_peer import Kea4PeerManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestKea4PeerCRUD:
    """DHCPv4 HA peer CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-peer",
                "role": "primary",
                "url": "http://10.99.0.1:8000/",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        """Same params -> noop."""
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-peer",
                "role": "primary",
                "url": "http://10.99.0.1:8000/",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update_url(self, opn_client: OpnsenseClient) -> None:
        """Update url field -> changed."""
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-peer",
                "role": "primary",
                "url": "http://10.99.0.2:8000/",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-peer-cm",
                "role": "standby",
                "url": "http://10.99.0.3:8000/",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-peer-cm")
        found = [row for row in rows if row.get("name") == "inttest-peer-cm"]
        assert found == []

    async def test_05_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4PeerManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-peer"})
        assert r.changed is True
        assert r.action == "deleted"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 peer matches same name."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two peers with same name via direct create."""
        mgr = Kea4PeerManager(opn_client)
        r1 = await mgr.create(
            params={
                "name": "inttest-dup-peer",
                "role": "primary",
                "url": "http://10.99.0.10:8000/",
            }
        )
        r2 = await mgr.create(
            params={
                "name": "inttest-dup-peer",
                "role": "standby",
                "url": "http://10.99.0.11:8000/",
            }
        )
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError."""
        mgr = Kea4PeerManager(opn_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "name": "inttest-dup-peer",
                    "role": "primary",
                    "url": "http://10.99.0.10:8000/",
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate peers by UUID."""
        mgr = Kea4PeerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-peer")
        for row in rows:
            if row.get("name") == "inttest-dup-peer":
                await mgr.delete(row["uuid"])
        rows = await mgr.list(search_phrase="inttest-dup-peer")
        remaining = [r for r in rows if r.get("name") == "inttest-dup-peer"]
        assert remaining == []


class TestFieldValidation:
    """Verify FieldValidationError for invalid input."""

    async def test_01_empty_name_rejected(self, opn_client: OpnsenseClient) -> None:
        """Empty required name -> FieldValidationError."""
        mgr = Kea4PeerManager(opn_client)
        with pytest.raises(FieldValidationError, match="name"):
            await mgr.ensure(
                "present",
                {"name": "", "role": "primary", "url": "http://10.99.0.1:8000/"},
            )

    async def test_02_bad_role_rejected(self, opn_client: OpnsenseClient) -> None:
        """Bad role enum -> FieldValidationError."""
        mgr = Kea4PeerManager(opn_client)
        with pytest.raises(FieldValidationError, match="role"):
            await mgr.ensure(
                "present",
                {"name": "inttest-bad-role", "role": "invalid", "url": "http://10.99.0.1:8000/"},
            )


class TestCleanup:
    """Remove all inttest- Kea DHCPv4 peers."""

    async def test_cleanup_peers(self, opn_client: OpnsenseClient) -> None:
        mgr = Kea4PeerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("kea/dhcpv4/delPeer", row["uuid"])
        await opn_client.reconfigure("kea/service/reconfigure", timeout=60)
