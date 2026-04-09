# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_conn -- IpsecConn."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.ipsec_conn import IpsecConn


class TestIpsecConn:
    """IpsecConn frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecConn(description="s2s").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecConn(description="s2s")
        assert obj.description == "s2s"

    def test_defaults(self) -> None:
        obj = IpsecConn(description="s2s")
        assert obj.enabled == "1"
        assert obj.version == ""
        assert obj.aggressive == "0"
        assert obj.mobike == "1"
        assert obj.reauth_time == ""
        assert obj.rekey_time == ""
        assert obj.dpd_delay == ""
        assert obj.dpd_timeout == ""
        assert obj.keyingtries == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecConn(
            description="site-to-site",
            enabled="1",
            version="2",
            aggressive="0",
            mobike="1",
            reauth_time="3600",
            rekey_time="14400",
            dpd_delay="30",
            dpd_timeout="150",
            keyingtries="3",
            uuid="uuid-1",
        )
        assert obj.description == "site-to-site"
        assert obj.version == "2"
        assert obj.dpd_delay == "30"
        assert obj.uuid == "uuid-1"
