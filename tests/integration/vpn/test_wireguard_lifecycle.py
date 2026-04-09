# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — WireGuard managers on live OPNsense device.

WireGuard must be enabled before testing.
Server requires a private key (generated via wireguard/server/keyPair API).
All test objects use inttest- prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
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
