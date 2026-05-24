# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — DnsmasqTagManager against a live OPNsense device.

Safety: tag names use the ``inttest-`` prefix; cleanup scoped to that prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.services.dnsmasq_tag import DnsmasqTagManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INTTEST_TAG = "inttesttag01"  # alphanumeric-only — API rejects hyphens/underscores
INTTEST_TAG_DUP = "inttestdup"
INTTEST_PREFIX = "inttest"


class TestDnsmasqTagCRUD:
    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        r = await mgr.ensure("present", {"tag": INTTEST_TAG})
        assert r.action == "created"
        assert r.uuid

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        r = await mgr.ensure("present", {"tag": INTTEST_TAG})
        assert r.action == "noop"

    async def test_03_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        r = await mgr.ensure("absent", {"tag": INTTEST_TAG})
        assert r.action == "deleted"

    async def test_04_delete_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        r = await mgr.ensure("absent", {"tag": INTTEST_TAG})
        assert r.action == "noop"


class TestUniquenessEnforced:
    """Server enforces unique ``tag`` (verified via probe: 'Tag names should
    be unique'). Ambiguity therefore cannot be triggered on a live device —
    AmbiguousMatchError remains covered in the unit suite (mocked search).
    """

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        r = await mgr.create(params={"tag": INTTEST_TAG_DUP})
        assert r.uuid

    async def test_02_second_create_rejected_by_server(self, opn_client: OpnsenseClient) -> None:
        from opnsense.exceptions import OpnsenseValidationError

        mgr = DnsmasqTagManager(opn_client)
        with pytest.raises(OpnsenseValidationError, match="unique"):
            await mgr.create(params={"tag": INTTEST_TAG_DUP})

    async def test_03_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("tag") == INTTEST_TAG_DUP:
                await mgr.delete(row["uuid"])


class TestFieldValidation:
    async def test_missing_tag(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        with pytest.raises(FieldValidationError, match="tag"):
            await mgr.ensure("present", {})


class TestCleanup:
    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqTagManager(opn_client)
        rows = await mgr.list()
        for row in rows:
            if row.get("tag", "").startswith(INTTEST_PREFIX):
                await opn_client.delete("dnsmasq/settings/delTag", row["uuid"])
