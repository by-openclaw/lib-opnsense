# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IPsec managers on live OPNsense device.

Tests connection, PSK, pool, VTI, keypair. All disabled, inttest- prefix.
Child/Local/Remote need parent connection UUID — tested in chain.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.vpn.ipsec_child import IpsecChildManager
from opnsense.managers.vpn.ipsec_conn import IpsecConnManager
from opnsense.managers.vpn.ipsec_local import IpsecLocalManager
from opnsense.managers.vpn.ipsec_pool import IpsecPoolManager
from opnsense.managers.vpn.ipsec_psk import IpsecPskManager
from opnsense.managers.vpn.ipsec_remote import IpsecRemoteManager
from opnsense.managers.vpn.ipsec_vti import IpsecVtiManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestIpsecConnCRUD:
    """IPsec connection CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecConnManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-ipsec-conn",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecConnManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-ipsec-conn"})
        assert r.changed is True
        assert r.action == "deleted"


class TestIpsecChain:
    """Connection → Child + Local + Remote chain."""

    async def test_01_create_conn(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecConnManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-chain-conn",
                "enabled": "0",
            },
        )
        assert r.action in ("created", "noop")

    async def test_02_create_child(self, opn_client: OpnsenseClient) -> None:
        conn_mgr = IpsecConnManager(opn_client)
        rows = await conn_mgr.list(search_phrase="inttest-chain-conn")
        conn = [r for r in rows if r.get("description") == "inttest-chain-conn"]
        assert len(conn) == 1

        mgr = IpsecChildManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-chain-child",
                "connection": conn[0]["uuid"],
                "enabled": "0",
            },
        )
        assert r.action in ("created", "noop")

    async def test_03_create_local(self, opn_client: OpnsenseClient) -> None:
        conn_mgr = IpsecConnManager(opn_client)
        rows = await conn_mgr.list(search_phrase="inttest-chain-conn")
        conn_uuid = [r for r in rows if r.get("description") == "inttest-chain-conn"][0]["uuid"]

        mgr = IpsecLocalManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-chain-local",
                "connection": conn_uuid,
                "enabled": "0",
            },
        )
        assert r.action in ("created", "noop")

    async def test_04_create_remote(self, opn_client: OpnsenseClient) -> None:
        conn_mgr = IpsecConnManager(opn_client)
        rows = await conn_mgr.list(search_phrase="inttest-chain-conn")
        conn_uuid = [r for r in rows if r.get("description") == "inttest-chain-conn"][0]["uuid"]

        mgr = IpsecRemoteManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-chain-remote",
                "connection": conn_uuid,
                "enabled": "0",
            },
        )
        assert r.action in ("created", "noop")


class TestIpsecPskCRUD:
    """Pre-shared key CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecPskManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-psk",
                "ident": "test@example.com",
                "Key": "inttest-secret-key-value",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecPskManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-psk"})
        assert r.changed is True


class TestIpsecPoolCRUD:
    """IP pool CRUD."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecPoolManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "inttest-pool",
                "addrs": "10.99.99.0/24",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecPoolManager(opn_client)
        r = await mgr.ensure("absent", {"name": "inttest-pool"})
        assert r.changed is True


class TestIpsecVtiCRUD:
    """VTI CRUD — plain IPs, no CIDR."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecVtiManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-vti",
                "reqid": "99",
                "local": "10.11.1.1",
                "remote": "10.99.99.1",
                "tunnel_local": "10.10.99.1",
                "tunnel_remote": "10.10.99.2",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecVtiManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-vti"})
        assert r.changed is True


class TestCleanup:
    """Remove all inttest- IPsec objects (children first, then connections)."""

    async def test_cleanup_children(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecChildManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("ipsec/connections/delChild", row["uuid"])

    async def test_cleanup_locals(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecLocalManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("ipsec/connections/delLocal", row["uuid"])

    async def test_cleanup_remotes(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecRemoteManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("ipsec/connections/delRemote", row["uuid"])

    async def test_cleanup_conns(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecConnManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("ipsec/connections/delConnection", row["uuid"])

    async def test_cleanup_psks(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecPskManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("ipsec/pre_shared_keys/delItem", row["uuid"])

    async def test_cleanup_pools(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecPoolManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("name", "")):
                await opn_client.delete("ipsec/pools/del", row["uuid"])

    async def test_cleanup_vtis(self, opn_client: OpnsenseClient) -> None:
        mgr = IpsecVtiManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("ipsec/vti/del", row["uuid"])
        await opn_client.reconfigure("ipsec/service/reconfigure", timeout=30)
