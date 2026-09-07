# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for the plugin general-settings singletons (chrony, lldpd, qemu-guest-agent,
dnscrypt-proxy).

Covers ADR ``lib/python/0001 §10.2`` for the singleton pattern, parametrised over the four
managers: endpoint binding + payload nesting, noop, update + reconfigure, check_mode,
multi-select normalisation / set comparison, validation, state handling, error propagation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseServerError
from opnsense.managers.dns.dnscrypt_general import DnscryptProxyGeneralManager
from opnsense.managers.services.chrony_general import ChronyGeneralManager
from opnsense.managers.services.lldpd_general import LldpdGeneralManager
from opnsense.managers.services.qemuguestagent_settings import QemuGuestAgentSettingsManager

# (manager, get endpoint, payload key, section, apply endpoint, enable field, multi field)
CASES = [
    (
        ChronyGeneralManager,
        "chrony/general",
        "general",
        None,
        "chrony/service/reconfigure",
        "enabled",
        "peers",
    ),
    (
        LldpdGeneralManager,
        "lldpd/general",
        "general",
        None,
        "lldpd/service/reconfigure",
        "enabled",
        "interface",
    ),
    (
        QemuGuestAgentSettingsManager,
        "qemuguestagent/settings",
        "qemuguestagent",
        "general",
        "qemuguestagent/service/reconfigure",
        "Enabled",
        "DisabledRPCs",
    ),
    (
        DnscryptProxyGeneralManager,
        "dnscryptproxy/general",
        "general",
        None,
        "dnscryptproxy/service/reconfigure",
        "enabled",
        "listen_addresses",
    ),
]
IDS = ["chrony", "lldpd", "qemuguestagent", "dnscrypt"]


def _doc(payload, section, inner):
    return {payload: ({section: inner} if section else inner)}


def _opts(*selected, extra=()):
    d = {k: {"value": k, "selected": 1} for k in selected}
    d.update({k: {"value": k, "selected": 0} for k in extra})
    return d


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,endpoint,payload,section,apply,enable,multi", CASES, ids=IDS)
class TestPluginGeneralSingleton:
    async def test_get_hits_endpoint_and_unwraps(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        mock_client.get.return_value = _doc(payload, section, {enable: "0"})
        mgr = cls(mock_client)
        assert await mgr.get() == {enable: "0"}
        mock_client.get.assert_awaited_once_with(f"{endpoint}/get")

    async def test_noop_when_matching(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        mock_client.get.return_value = _doc(payload, section, {enable: "1"})
        result = await cls(mock_client).ensure("present", {enable: "1"})
        assert result.changed is False and result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_update_posts_nested_payload_and_reconfigures(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        mock_client.get.side_effect = [
            _doc(payload, section, {enable: "0"}),
            _doc(payload, section, {enable: "1"}),
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        result = await cls(mock_client).ensure("present", {enable: "1"})
        assert result.changed is True and result.action == "updated"
        mock_client.post.assert_awaited_once_with(
            f"{endpoint}/set", _doc(payload, section, {enable: "1"})
        )
        mock_client.reconfigure.assert_awaited_once_with(apply, timeout=60)

    async def test_check_mode_does_not_post(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        mock_client.get.return_value = _doc(payload, section, {enable: "0"})
        result = await cls(mock_client).ensure("present", {enable: "1"}, check_mode=True)
        assert result.changed is True
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_multi_select_list_normalised_and_set_compared(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        current = _doc(payload, section, {enable: "1", multi: _opts("a", "b", extra=("c",))})
        mock_client.get.return_value = current
        mgr = cls(mock_client)
        # same selection, different order -> noop
        result = await mgr.ensure("present", {multi: ["b", "a"]})
        assert result.action == "noop"
        # different selection -> POST with CSV
        mock_client.get.side_effect = [
            current,
            _doc(payload, section, {enable: "1", multi: _opts("a", "c")}),
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        result = await mgr.ensure("present", {multi: ["a", "c"]})
        assert result.changed is True
        mock_client.post.assert_awaited_once_with(
            f"{endpoint}/set", _doc(payload, section, {multi: "a,c"})
        )

    async def test_invalid_bool_rejected_before_api(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        with pytest.raises(FieldValidationError):
            await cls(mock_client).ensure("present", {enable: "yes"})
        mock_client.get.assert_not_awaited()

    async def test_rejects_state_absent(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        with pytest.raises(ValueError):
            await cls(mock_client).ensure("absent", {})

    async def test_server_error_propagates(
        self, mock_client: AsyncMock, cls, endpoint, payload, section, apply, enable, multi
    ):
        mock_client.get.return_value = _doc(payload, section, {enable: "0"})
        mock_client.post.side_effect = OpnsenseServerError("boom")
        with pytest.raises(OpnsenseServerError):
            await cls(mock_client).ensure("present", {enable: "1"})
