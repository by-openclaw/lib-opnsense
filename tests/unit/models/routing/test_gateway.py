# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.rt_gateway -- RtGateway."""

from __future__ import annotations

import pytest

from opnsense.models.rt_gateway import RtGateway


class TestRtGateway:
    """RtGateway frozen dataclass -- single key (name)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            RtGateway(name="WAN_GW").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        gw = RtGateway(name="WAN_GW")
        assert gw.name == "WAN_GW"

    def test_defaults(self) -> None:
        gw = RtGateway(name="WAN_GW")
        assert gw.interface == ""
        assert gw.gateway == ""
        assert gw.ipprotocol == "inet"
        assert gw.defaultgw == "0"
        assert gw.disabled == "0"
        assert gw.descr == ""
        assert gw.priority == "255"
        assert gw.weight == "1"
        assert gw.uuid == ""
