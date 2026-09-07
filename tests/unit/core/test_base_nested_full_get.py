# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests — BaseManager.ensure() fetches the FULL item when params carry nested dicts.

Search rows are flat (Kea subnet ``option_data`` is absent), so a diff against the row ignored
nested blocks entirely (#85). With a nested dict in the desired params the base now reads the
item by uuid before diffing; flat params keep the single-search behaviour.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.base import BaseManager


class _Subnet(BaseManager):
    _endpoint = "kea/dhcpv4"
    _payload_key = "subnet4"
    _entity_suffix = "Subnet"
    _apply_endpoint = "kea/service/reconfigure"
    _match_key = "subnet"
    _validators = {"subnet": {"type": "str", "required": True}, "option_data": {"type": "dict"}}


ROW = {"uuid": "u-1", "subnet": "10.1.1.0/24", "description": "mgmt"}
FULL = {
    "subnet": "10.1.1.0/24",
    "description": "mgmt",
    "option_data": {"routers": "10.1.1.1", "ntp_servers": ""},
}


@pytest.mark.asyncio
class TestNestedFullGet:
    async def test_nested_drift_detected_via_full_get(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [ROW]
        mock_client.get.return_value = {"subnet4": FULL}
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await _Subnet(mock_client).ensure(
            "present",
            {
                "subnet": "10.1.1.0/24",
                "option_data": {"routers": "10.1.1.1", "ntp_servers": "10.1.1.1"},
            },
        )
        assert r.changed is True and r.action == "updated"
        # first get = the full item before the diff (the update path re-reads afterwards)
        assert mock_client.get.await_args_list[0].args[0].endswith("/getSubnet/u-1")

    async def test_nested_equal_is_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [ROW]
        mock_client.get.return_value = {"subnet4": FULL}
        r = await _Subnet(mock_client).ensure(
            "present", {"subnet": "10.1.1.0/24", "option_data": {"routers": "10.1.1.1"}}
        )
        assert r.changed is False and r.action == "noop"
        mock_client.update.assert_not_awaited()

    async def test_flat_params_do_not_fetch(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [ROW]
        r = await _Subnet(mock_client).ensure(
            "present", {"subnet": "10.1.1.0/24", "description": "mgmt"}
        )
        assert r.action == "noop"
        mock_client.get.assert_not_awaited()
