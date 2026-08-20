# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — CrowdSec managers against a live OPNsense device.

Safety boundaries:
    - Read paths (``get``, ``status``) and check-mode diffs are always safe and
      always run.
    - An idempotent ``ensure`` back to the values already on the device is
      exercised, so no state transition occurs.
    - A REAL settings write only runs when ``OPN_CROWDSEC_ALLOW_WRITE=1``. It
      writes ``rules_tag`` — a free-form label with no enforcement effect — and
      restores the original value afterwards. It never touches
      ``agent_enabled`` / ``lapi_enabled`` / ``firewall_bouncer_enabled``,
      because flipping those on a production firewall changes whether traffic
      is being filtered.
    - ``crowdsec/decisions/del`` is never called: dropping an active ban is
      destructive and unrecoverable from the test's point of view.
    - The service is never started, stopped or restarted here.
"""

from __future__ import annotations

import os

import pytest
from opnsense.client import OpnsenseClient
from opnsense.managers.crowdsec.service import CrowdSecServiceManager
from opnsense.managers.crowdsec.settings import CrowdSecSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_ALLOW_WRITE = os.environ.get("OPN_CROWDSEC_ALLOW_WRITE") == "1"

_BOOL_FIELDS = (
    "agent_enabled",
    "lapi_enabled",
    "firewall_bouncer_enabled",
    "lapi_manual_configuration",
)


class TestSettingsReadOnly:
    """Read-only checks — always safe."""

    async def test_get_returns_expected_fields(self, opn_client: OpnsenseClient) -> None:
        mgr = CrowdSecSettingsManager(opn_client)
        cfg = await mgr.get()
        for field in _BOOL_FIELDS:
            assert field in cfg, f"missing {field} in crowdsec/general/get"
            assert cfg[field] in ("0", "1"), f"{field} not a bool string: {cfg[field]!r}"
        assert "lapi_listen_port" in cfg

    async def test_ensure_current_values_is_noop(self, opn_client: OpnsenseClient) -> None:
        """Re-asserting the live values must not change anything."""
        mgr = CrowdSecSettingsManager(opn_client)
        cfg = await mgr.get()
        result = await mgr.ensure(
            "present", {"firewall_bouncer_enabled": cfg["firewall_bouncer_enabled"]}
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_check_mode_reports_without_writing(self, opn_client: OpnsenseClient) -> None:
        """check_mode must detect drift but leave the device untouched."""
        mgr = CrowdSecSettingsManager(opn_client)
        before = await mgr.get()
        flipped = "0" if before["crowdsec_firewall_verbose"] == "1" else "1"
        result = await mgr.ensure(
            "present", {"crowdsec_firewall_verbose": flipped}, check_mode=True
        )
        assert result.changed is True
        after = await mgr.get()
        assert after["crowdsec_firewall_verbose"] == before["crowdsec_firewall_verbose"]

    async def test_enroll_key_never_surfaces(self, opn_client: OpnsenseClient) -> None:
        """A noop ensure must not leak enroll_key through the result."""
        mgr = CrowdSecSettingsManager(opn_client)
        cfg = await mgr.get()
        key = cfg.get("enroll_key") or ""
        result = await mgr.ensure("present", {"rules_tag": cfg.get("rules_tag", "")})
        if key:
            assert key not in str(result.before)
            assert key not in str(result.after)


class TestServiceReadOnly:
    """Service status — read-only, never transitions state."""

    async def test_status_is_known_value(self, opn_client: OpnsenseClient) -> None:
        mgr = CrowdSecServiceManager(opn_client)
        status = await mgr.status()
        assert status in (
            "running",
            "stopped",
            "disabled",
            "unknown",
        ), f"unexpected crowdsec status: {status!r}"

    async def test_ensure_current_state_is_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = CrowdSecServiceManager(opn_client)
        status = await mgr.status()
        if status not in ("running", "stopped"):
            pytest.skip(f"service in state {status!r}; no safe idempotent target")
        target = "running" if status == "running" else "stopped"
        result = await mgr.ensure(target)
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.skipif(not _ALLOW_WRITE, reason="set OPN_CROWDSEC_ALLOW_WRITE=1 to enable")
class TestSettingsWrite:
    """One real write, on a label field, restored afterwards."""

    async def test_rules_tag_roundtrip(self, opn_client: OpnsenseClient) -> None:
        mgr = CrowdSecSettingsManager(opn_client)
        original = (await mgr.get()).get("rules_tag", "")
        probe = "libopnsenseitest"  # alphanumeric only — the API rejects hyphens
        try:
            first = await mgr.ensure("present", {"rules_tag": probe})
            assert first.changed is True
            assert (await mgr.get())["rules_tag"] == probe

            # Second identical ensure must be a noop — the idempotency contract.
            second = await mgr.ensure("present", {"rules_tag": probe})
            assert second.changed is False
            assert second.action == "noop"
        finally:
            await mgr.ensure("present", {"rules_tag": original})
            assert (await mgr.get()).get("rules_tag", "") == original
