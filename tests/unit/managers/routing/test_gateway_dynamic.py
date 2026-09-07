# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests — RtGatewayManager on DYNAMIC gateways (no static ``gateway`` address).

PPPoE / DHCP / DHCP6-PD gateways exist on the device with ``gateway=None``; the catalog
only pins their ``monitor``. They must be matched by name and updated without ``gateway``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.routing.gateway import RtGatewayManager

_DYN = {
    "uuid": "u-1",
    "name": "WAN_PROXIMUS_DHCP6",
    "interface": "opt12",
    "ipprotocol": "inet6",
    "gateway": None,
    "monitor": "2620:fe::fe",
    "monitor_disable": "0",
}


@pytest.mark.asyncio
class TestDynamicGateway:
    async def test_monitor_update_without_gateway(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [_DYN]
        mock_client.get.return_value = {"gateway_item": {**_DYN, "monitor": "2001:4860:4860::8888"}}
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = RtGatewayManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "name": "WAN_PROXIMUS_DHCP6",
                "interface": "opt12",
                "ipprotocol": "inet6",
                "monitor": "2001:4860:4860::8888",
            },
        )
        assert r.changed is True and r.action == "updated"
        mock_client.create.assert_not_awaited()

    async def test_monitor_noop_when_equal(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [_DYN]
        mgr = RtGatewayManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"name": "WAN_PROXIMUS_DHCP6", "interface": "opt12", "monitor": "2620:fe::fe"},
        )
        assert r.changed is False and r.action == "noop"
        mock_client.update.assert_not_awaited()
