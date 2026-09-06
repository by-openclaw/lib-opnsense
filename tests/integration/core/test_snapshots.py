# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — core/snapshots (ZFS boot environments) against a live device.

Requirements:
    - Live OPNsense on a ZFS-root install (OPN_HOST/OPN_KEY/OPN_SECRET env vars).
    - Skips automatically if the install does not support snapshots (UFS).
    - Run: pytest tests/integration/core/test_snapshots.py -v

Lifecycle covered: supported-check, create (C), idempotent (I), check-mode (K),
read/list (R), activate-noop, delete (D), delete-noop (Dn), cleanup (X).
All objects use the prefix 'inttest-snap-' to avoid touching real boot envs.
"""

from __future__ import annotations

import pytest

from opnsense.managers.core.snapshots import CoreSnapshotManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

NAME = "inttest-snap-lifecycle"


@pytest.fixture
async def mgr(opn_client):
    m = CoreSnapshotManager(opn_client)
    if not await m.is_supported():
        pytest.skip("snapshots not supported (non-ZFS install)")
    # pre-clean
    await m.ensure("absent", NAME)
    yield m
    # post-clean
    await m.ensure("absent", NAME)


async def test_create(mgr):
    r = await mgr.ensure("present", NAME)
    assert r.changed is True
    assert r.action == "created"
    assert r.uuid


async def test_idempotent(mgr):
    await mgr.ensure("present", NAME)
    r = await mgr.ensure("present", NAME)
    assert r.changed is False
    assert r.action == "noop"


async def test_check_mode_create(mgr):
    r = await mgr.ensure("present", NAME + "-ck", check_mode=True)
    assert r.changed is True and r.action == "created"
    assert await mgr._find(NAME + "-ck") is None  # nothing actually created


async def test_list_contains(mgr):
    await mgr.ensure("present", NAME)
    names = [row.get("name") for row in await mgr.list()]
    assert NAME in names


async def test_delete_and_noop(mgr):
    await mgr.ensure("present", NAME)
    r = await mgr.ensure("absent", NAME)
    assert r.changed is True and r.action == "deleted"
    r2 = await mgr.ensure("absent", NAME)
    assert r2.changed is False and r2.action == "noop"


async def test_activate_missing_raises(mgr):
    with pytest.raises(KeyError):
        await mgr.activate("inttest-snap-does-not-exist")
