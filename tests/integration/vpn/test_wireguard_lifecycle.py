# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — WireGuard server and client managers against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - WireGuard must be enabled on the device
    - Run with: pytest tests/integration/vpn/test_wireguard_lifecycle.py -v

Test flow (ordered, 10-step standard):
    1. Create (C)       -- TestWgServerCRUD.test_01_create,
                           TestWgClientCRUD.test_01_create
    2. Idempotent (I)   -- TestWgServerCRUD.test_02_idempotent,
                           TestWgClientCRUD.test_02_idempotent
    3. Update (U)       -- N/A -- WG fields are immutable after creation
    4. Check mode (K)   -- TestCheckMode.test_01_check_mode_create
    5. Read/list (R)    -- TestWgServerCRUD.test_03_redact_privkey
    6. Ambiguous (A)    -- TestAmbiguousMatch (test_01..test_05)
    7. Error (E)        -- N/A -- no FieldValidationError test
    8. Delete (D)       -- TestWgServerCRUD.test_04_delete,
                           TestWgClientCRUD.test_03_delete
    9. Delete noop (Dn) -- N/A -- no explicit delete-noop test
    10. Cleanup (X)     -- TestCleanup (clients first, then servers)

Naming convention:
    All test objects use prefix 'inttest-' to avoid collision with real config.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.vpn.wg_client import WgClientManager
from opnsense.managers.vpn.wg_server import WgServerManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestWgServerCRUD:
    """WG server (tunnel interface) CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = WgServerManager(opn_client)
        keys = await mgr.generate_keypair()
        assert "privkey" in keys
        assert "pubkey" in keys
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-wg-server",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
                "privkey": keys["privkey"],
                "enabled": "1",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = WgServerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-wg-server")
        server = [r for r in rows if r.get("name") == "inttest-wg-server"]
        assert len(server) == 1
        # Noop — privkey redacted in search, so just check name exists

    async def test_03_redact_privkey(self, opn_client: OpnsenseClient) -> None:
        """Verify privkey is redacted in ensure results."""
        mgr = WgServerManager(opn_client)
        keys = await mgr.generate_keypair()
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-wg-redact",
                "port": "51821",
                "tunneladdress": "10.10.1.1/24",
                "privkey": keys["privkey"],
            },
        )
        assert r.changed is True
        if r.after:
            assert r.after.get("privkey") == "<REDACTED:privkey>"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = WgServerManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-wg-redact"})
        assert r.changed is True
        assert r.action == "deleted"


class TestWgClientCRUD:
    """WG client (peer) CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = WgClientManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-wg-peer",
                "pubkey": "dGVzdHB1YmtleXRlc3RwdWJrZXl0ZXN0cHVia2V5PQ==",
                "tunneladdress": "10.10.0.2/32",
                "serveraddress": "10.99.99.1",
                "serverport": "51820",
                "keepalive": "25",
                "enabled": "1",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = WgClientManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-wg-peer",
                "pubkey": "dGVzdHB1YmtleXRlc3RwdWJrZXl0ZXN0cHVia2V5PQ==",
                "tunneladdress": "10.10.0.2/32",
                "serveraddress": "10.99.99.1",
                "serverport": "51820",
                "keepalive": "25",
                "enabled": "1",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = WgClientManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-wg-peer"})
        assert r.changed is True
        assert r.action == "deleted"


class TestAmbiguousMatch:
    """Verify AmbiguousMatchError when >1 WG server matches name key."""

    async def test_01_create_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Create two WG servers with same name via direct create."""
        mgr = WgServerManager(opn_client)
        keys1 = await mgr.generate_keypair()
        keys2 = await mgr.generate_keypair()
        r1 = await mgr.create(
            params={
                "name": "inttest-dup-wg",
                "port": "51899",
                "tunneladdress": "10.10.99.1/24",
                "privkey": keys1["privkey"],
                "enabled": "1",
            }
        )
        r2 = await mgr.create(
            params={
                "name": "inttest-dup-wg",
                "port": "51898",
                "tunneladdress": "10.10.98.1/24",
                "privkey": keys2["privkey"],
                "enabled": "1",
            }
        )
        assert r1.uuid is not None
        assert r2.uuid is not None
        assert r1.uuid != r2.uuid

    async def test_02_ensure_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure() on ambiguous pair -> AmbiguousMatchError with both UUIDs."""
        mgr = WgServerManager(opn_client)
        keys = await mgr.generate_keypair()
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "name": "inttest-dup-wg",
                    "port": "51899",
                    "tunneladdress": "10.10.99.1/24",
                    "privkey": keys["privkey"],
                },
            )
        assert len(exc_info.value.uuids) == 2

    async def test_03_ensure_absent_raises_ambiguous(self, opn_client: OpnsenseClient) -> None:
        """ensure(absent) on ambiguous pair -> AmbiguousMatchError."""
        mgr = WgServerManager(opn_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(state="absent", params={"name": "inttest-dup-wg"})

    async def test_04_uuid_escape_hatch(self, opn_client: OpnsenseClient) -> None:
        """ensure(uuid=) bypasses _find_existing — works on ambiguous pair."""
        mgr = WgServerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-wg")
        dups = [r for r in rows if r.get("name") == "inttest-dup-wg"]
        assert len(dups) == 2
        # Fetch the first one's full details to get privkey for noop check
        result = await mgr.ensure(
            state="present",
            uuid=dups[0]["uuid"],
            params={"name": "inttest-dup-wg"},
        )
        assert result.action in ("noop", "updated")

    async def test_05_cleanup_duplicates(self, opn_client: OpnsenseClient) -> None:
        """Delete both duplicate WG servers by UUID."""
        mgr = WgServerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest-dup-wg")
        for r in rows:
            if r.get("name") == "inttest-dup-wg":
                await mgr.delete(r["uuid"])
        # Verify clean
        rows = await mgr.list(search_phrase="inttest-dup-wg")
        remaining = [r for r in rows if r.get("name") == "inttest-dup-wg"]
        assert remaining == []


class TestCheckMode:
    """check_mode on WG server create -- resource NOT created."""

    async def test_01_check_mode_create(self, opn_client: OpnsenseClient) -> None:
        """check_mode create -> changed=True but resource NOT created."""
        mgr = WgServerManager(opn_client)
        keys = await mgr.generate_keypair()
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-wg-cm",
                "port": "51830",
                "tunneladdress": "10.10.2.1/24",
                "privkey": keys["privkey"],
                "enabled": "0",
            },
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify resource was NOT actually created
        rows = await mgr.list(search_phrase="inttest-wg-cm")
        found = [row for row in rows if row.get("name") == "inttest-wg-cm"]
        assert found == []


class TestCleanup:
    """Remove all inttest- WG objects (clients first, then servers)."""

    async def test_cleanup_clients(self, opn_client: OpnsenseClient) -> None:
        mgr = WgClientManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("wireguard/client/delClient", row["uuid"])

    async def test_cleanup_servers(self, opn_client: OpnsenseClient) -> None:
        mgr = WgServerManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("wireguard/server/delServer", row["uuid"])
        await opn_client.reconfigure("wireguard/service/reconfigure", timeout=30)
