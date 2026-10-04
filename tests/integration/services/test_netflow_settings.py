# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — NetFlow / Insight settings against a live OPNsense device.

Safety boundaries:
    - read, ensure-to-current-value (noop) and check_mode never modify the device.
    - the one write test narrows the capture list to a single interface and ALWAYS restores
      the original document (try/finally); flow accounting has no forwarding impact.
    - an invalid interface is refused by the API: nothing is saved.
"""

from __future__ import annotations

from typing import Any

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.services.netflow_settings import NetflowSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _selected(value: Any) -> list[str]:
    """Selected keys of an option dict (or the tokens of a CSV string)."""
    if isinstance(value, dict):
        return [
            k for k, v in value.items() if isinstance(v, dict) and str(v.get("selected")) == "1"
        ]
    return [tok for tok in str(value).split(",") if tok]


def _document(settings: dict[str, Any]) -> dict[str, Any]:
    """The live settings as a desired document (what ensure() takes)."""
    capture = settings["capture"]
    return {
        "capture": {
            "interfaces": _selected(capture["interfaces"]),
            "egress_only": _selected(capture["egress_only"]),
            "version": _selected(capture["version"])[0],
            "targets": _selected(capture["targets"]),
        },
        "collect": {"enable": settings["collect"]["enable"]},
    }


class TestNetflowSettings:
    async def test_01_get_returns_the_nested_document(self, opn_client: OpnsenseClient) -> None:
        settings = await NetflowSettingsManager(opn_client).get()
        assert {"capture", "collect"} <= set(settings)
        assert {"interfaces", "egress_only", "version", "targets"} <= set(settings["capture"])
        assert settings["collect"]["enable"] in ("0", "1")

    async def test_02_ensure_current_is_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = NetflowSettingsManager(opn_client)
        r = await mgr.ensure("present", _document(await mgr.get()))
        assert r.action == "noop" and r.changed is False

    async def test_03_check_mode_reports_and_does_not_modify(
        self, opn_client: OpnsenseClient
    ) -> None:
        mgr = NetflowSettingsManager(opn_client)
        before = _document(await mgr.get())
        flipped = "0" if before["collect"]["enable"] == "1" else "1"
        r = await mgr.ensure("present", {"collect": {"enable": flipped}}, check_mode=True)
        assert r.changed is True and r.action == "updated"
        assert _document(await mgr.get()) == before

    async def test_04_change_applies_and_is_idempotent_then_restored(
        self, opn_client: OpnsenseClient
    ) -> None:
        mgr = NetflowSettingsManager(opn_client)
        original = _document(await mgr.get())
        offered = sorted((await mgr.get())["capture"]["interfaces"])
        target = [offered[0]]
        if sorted(original["capture"]["interfaces"]) == target:
            target = [offered[-1]]
        desired = {"capture": {**original["capture"], "interfaces": target, "egress_only": []}}
        try:
            r = await mgr.ensure("present", desired)
            assert r.changed is True and r.action == "updated"
            assert _document(await mgr.get())["capture"]["interfaces"] == target
            again = await mgr.ensure("present", desired)
            assert again.changed is False and again.action == "noop"
        finally:
            await mgr.ensure("present", original)
        assert _document(await mgr.get()) == original

    async def test_05_unknown_interface_is_refused_by_the_api(
        self, opn_client: OpnsenseClient
    ) -> None:
        mgr = NetflowSettingsManager(opn_client)
        before = _document(await mgr.get())
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure("present", {"capture": {"interfaces": ["inttest-nosuchif"]}})
        assert "netflow.capture.interfaces" in exc_info.value.validations
        assert _document(await mgr.get()) == before
