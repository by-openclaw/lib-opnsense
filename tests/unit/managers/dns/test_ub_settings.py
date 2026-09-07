# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.dns.ub_settings.UbSettingsManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set, adapted for the
singleton pattern. Most behaviour is inherited from ``BaseSingletonManager``
(``_section='general'``); these tests verify endpoint binding, the
general-block unwrap/re-nest, validator wiring and multi-select handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    FieldValidationError,
    OpnsenseServerError,
    OpnsenseValidationError,
)
from opnsense.managers.dns.ub_settings import UbSettingsManager

_DOC_DISABLED = {
    "unbound": {
        "general": {
            "enabled": "0",
            "port": "53",
            "active_interface": {
                "lan": {"value": "LAN", "selected": 0},
                "opt1": {"value": "DMZ", "selected": 0},
            },
            "local_zone_type": {
                "transparent": {"value": "Transparent", "selected": 1},
                "static": {"value": "Static", "selected": 0},
            },
        },
        "advanced": {"prefetch": "0"},
    }
}


def _doc(**general: object) -> dict:
    body = {
        "unbound": {
            "general": {**_DOC_DISABLED["unbound"]["general"], **general},
            "advanced": {"prefetch": "0"},
        }
    }
    return body


@pytest.mark.asyncio
class TestGet:
    async def test_get_unwraps_general_block(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _DOC_DISABLED
        mgr = UbSettingsManager(mock_client)
        result = await mgr.get()
        assert result["enabled"] == "0"
        assert "advanced" not in result
        mock_client.get.assert_awaited_once_with("unbound/settings/get")

    async def test_get_returns_empty_when_no_general(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"unbound": {"advanced": {}}}
        mgr = UbSettingsManager(mock_client)
        assert await mgr.get() == {}


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _DOC_DISABLED
        mgr = UbSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "0", "port": "53"})
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_enable_posts_nested_general_and_reconfigures(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get.side_effect = [_DOC_DISABLED, _doc(enabled="1")]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = UbSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "1"})
        assert result.changed is True
        assert result.action == "updated"
        assert result.after["enabled"] == "1"
        mock_client.post.assert_awaited_once_with(
            "unbound/settings/set",
            {"unbound": {"general": {"enabled": "1"}}},
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "unbound/service/reconfigure",
            timeout=60,
        )

    async def test_check_mode_does_not_post(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _DOC_DISABLED
        mgr = UbSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "1"}, check_mode=True)
        assert result.changed is True
        assert result.action == "updated"
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_multi_select_list_is_normalised_to_csv(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            _DOC_DISABLED,
            _doc(
                active_interface={
                    "lan": {"value": "LAN", "selected": 1},
                    "opt1": {"value": "DMZ", "selected": 1},
                }
            ),
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = UbSettingsManager(mock_client)
        await mgr.ensure("present", {"active_interface": ["lan", "opt1"]})
        mock_client.post.assert_awaited_once_with(
            "unbound/settings/set",
            {"unbound": {"general": {"active_interface": "lan,opt1"}}},
        )

    async def test_multi_select_noop_ignores_order_and_empty_means_none(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = _doc(
            active_interface={
                "lan": {"value": "LAN", "selected": 1},
                "opt1": {"value": "DMZ", "selected": 1},
            }
        )
        mgr = UbSettingsManager(mock_client)
        result = await mgr.ensure("present", {"active_interface": "opt1,lan"})
        assert result.action == "noop"
        # none selected on the device == "" desired (all interfaces)
        mock_client.get.return_value = _DOC_DISABLED
        result = await mgr.ensure("present", {"active_interface": ""})
        assert result.action == "noop"

    async def test_enum_selected_value_is_compared(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _DOC_DISABLED
        mgr = UbSettingsManager(mock_client)
        result = await mgr.ensure("present", {"local_zone_type": "transparent"})
        assert result.action == "noop"

    async def test_rejects_state_absent(self, mock_client: AsyncMock) -> None:
        mgr = UbSettingsManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("absent", {})


@pytest.mark.asyncio
class TestValidation:
    async def test_invalid_bool_rejected_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = UbSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"enabled": "yes"})
        mock_client.get.assert_not_awaited()

    async def test_invalid_local_zone_type_rejected(self, mock_client: AsyncMock) -> None:
        mgr = UbSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"local_zone_type": "bogus"})

    async def test_port_too_long_rejected(self, mock_client: AsyncMock) -> None:
        mgr = UbSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"port": "123456"})


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_server_error_on_set_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _DOC_DISABLED
        mock_client.post.side_effect = OpnsenseServerError("boom")
        mgr = UbSettingsManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("present", {"enabled": "1"})

    async def test_validation_error_on_set_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _DOC_DISABLED
        mock_client.post.side_effect = OpnsenseValidationError(
            "failed", validations={"unbound.general.port": "invalid"}
        )
        mgr = UbSettingsManager(mock_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure("present", {"port": "0"})
