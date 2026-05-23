# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.dnsmasq_settings.DnsmasqSettingsManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set, adapted for the
singleton pattern. Most behavior is inherited from ``BaseSingletonManager``;
these tests verify endpoint binding, validator wiring, and the multi-select
normalization helper.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    FieldValidationError,
    OpnsenseServerError,
    OpnsenseValidationError,
)
from opnsense.managers.services.dnsmasq_settings import (
    DnsmasqSettingsManager,
    _normalize_multi_select,
)


class TestMultiSelectNormalization:
    """The multi-select helper accepts list/tuple/set/str and returns CSV."""

    def test_string_passes_through(self) -> None:
        assert _normalize_multi_select("lan,opt2") == "lan,opt2"

    def test_list_joined_with_comma(self) -> None:
        assert _normalize_multi_select(["lan", "opt2"]) == "lan,opt2"

    def test_tuple_joined(self) -> None:
        assert _normalize_multi_select(("a", "b", "c")) == "a,b,c"

    def test_empty_list_yields_empty_string(self) -> None:
        assert _normalize_multi_select([]) == ""

    def test_none_yields_empty_string(self) -> None:
        assert _normalize_multi_select(None) == ""


@pytest.mark.asyncio
class TestEnsure:
    async def test_get_hits_dnsmasq_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dnsmasq": {"enable": "1", "port": "53053"}}
        mgr = DnsmasqSettingsManager(mock_client)
        result = await mgr.get()
        assert result == {"enable": "1", "port": "53053"}
        mock_client.get.assert_awaited_once_with("dnsmasq/settings/get")

    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dnsmasq": {"enable": "0", "port": "53053"}}
        mgr = DnsmasqSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enable": "0"})
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_updates_when_drifted(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"dnsmasq": {"enable": "1", "port": "53053"}},
            {"dnsmasq": {"enable": "0", "port": "53053"}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DnsmasqSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enable": "0"})

        assert result.changed is True
        assert result.action == "updated"
        mock_client.post.assert_awaited_once_with(
            "dnsmasq/settings/set",
            {"dnsmasq": {"enable": "0"}},
        )
        mock_client.reconfigure.assert_awaited_once_with("dnsmasq/service/reconfigure", timeout=60)

    async def test_interface_list_normalized_to_csv_string(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"dnsmasq": {"interface": "lan"}},
            {"dnsmasq": {"interface": "lan,opt2"}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DnsmasqSettingsManager(mock_client)
        await mgr.ensure("present", {"interface": ["lan", "opt2"]})

        sent = mock_client.post.await_args.args[1]
        assert sent == {"dnsmasq": {"interface": "lan,opt2"}}

    async def test_check_mode_does_not_post(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dnsmasq": {"enable": "1"}}
        mgr = DnsmasqSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enable": "0"}, check_mode=True)
        assert result.changed is True
        assert result.action == "updated"
        mock_client.post.assert_not_awaited()


@pytest.mark.asyncio
class TestValidation:
    """ADR §10.2 case 3 — field validation runs before any API call."""

    async def test_invalid_bool_rejected(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"enable": "not-a-bool"})
        mock_client.get.assert_not_awaited()

    async def test_invalid_add_mac_enum_rejected(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"add_mac": "invalid"})
        mock_client.get.assert_not_awaited()

    async def test_state_absent_rejected(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqSettingsManager(mock_client)
        with pytest.raises(ValueError, match="state='present'"):
            await mgr.ensure("absent", {"enable": "0"})


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_server_validation_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dnsmasq": {"enable": "1"}}
        mock_client.post.side_effect = OpnsenseValidationError("server rejected")
        mgr = DnsmasqSettingsManager(mock_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure("present", {"enable": "0"})

    async def test_server_error_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dnsmasq": {"enable": "1"}}
        mock_client.post.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqSettingsManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("present", {"enable": "0"})
