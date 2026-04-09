# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.wg_server — WgServer."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.wg_server import WgServer


class TestWgServer:
    """WgServer frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            WgServer(name="wg0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = WgServer(name="wg0")
        assert obj.name == "wg0"

    def test_defaults(self) -> None:
        obj = WgServer(name="wg0")
        assert obj.enabled == "1"
        assert obj.port == ""
        assert obj.mtu == ""
        assert obj.tunneladdress == ""
        assert obj.dns == ""
        assert obj.disableroutes == "0"
        assert obj.gateway == ""
        assert obj.privkey == ""
        assert obj.pubkey == ""
        assert obj.peers == ""
        assert obj.uuid == ""
