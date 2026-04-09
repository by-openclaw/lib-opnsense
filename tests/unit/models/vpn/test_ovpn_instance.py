# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ovpn_instance -- OvpnInstance."""

from __future__ import annotations

import pytest

from opnsense.models.ovpn_instance import OvpnInstance


class TestOvpnInstance:
    """OvpnInstance frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            OvpnInstance(description="vpn0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = OvpnInstance(description="vpn0")
        assert obj.description == "vpn0"

    def test_defaults(self) -> None:
        obj = OvpnInstance(description="vpn0")
        assert obj.enabled == "1"
        assert obj.role == "server"
        assert obj.dev_type == "tun"
        assert obj.proto == "udp"
        assert obj.port == ""
        assert obj.server == ""
        assert obj.server_ipv6 == ""
        assert obj.cert == ""
        assert obj.ca == ""
        assert obj.auth == ""
        assert obj.topology == "subnet"
        assert obj.local == ""
        assert obj.remote == ""
        assert obj.keepalive_interval == ""
        assert obj.keepalive_timeout == ""
        assert obj.tun_mtu == ""
        assert obj.maxclients == ""
        assert obj.redirect_gateway == ""
        assert obj.username == ""
        assert obj.password == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = OvpnInstance(
            description="office-vpn",
            enabled="1",
            role="server",
            dev_type="tun",
            proto="udp",
            port="1194",
            server="10.8.0.0/24",
            server_ipv6="fd00::/64",
            cert="abc123",
            ca="ca456",
            auth="SHA256",
            topology="subnet",
            local="0.0.0.0",
            remote="vpn.example.com",
            keepalive_interval="10",
            keepalive_timeout="60",
            tun_mtu="1500",
            maxclients="100",
            redirect_gateway="def1",
            username="user1",
            password="secret",
            uuid="uuid-1",
        )
        assert obj.description == "office-vpn"
        assert obj.port == "1194"
        assert obj.server == "10.8.0.0/24"
        assert obj.cert == "abc123"
        assert obj.ca == "ca456"
        assert obj.uuid == "uuid-1"
