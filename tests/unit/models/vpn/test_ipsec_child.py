# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_child -- IpsecChild."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.ipsec_child import IpsecChild


class TestIpsecChild:
    """IpsecChild frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecChild(description="child0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecChild(description="child0")
        assert obj.description == "child0"

    def test_defaults(self) -> None:
        obj = IpsecChild(description="child0")
        assert obj.enabled == "1"
        assert obj.connection == ""
        assert obj.mode == "tunnel"
        assert obj.policies == "1"
        assert obj.rekey_time == "3600"
        assert obj.sha256_96 == "0"
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecChild(
            description="lan-to-lan",
            enabled="1",
            connection="conn-uuid-1",
            mode="tunnel",
            policies="1",
            rekey_time="7200",
            sha256_96="0",
            uuid="uuid-1",
        )
        assert obj.description == "lan-to-lan"
        assert obj.connection == "conn-uuid-1"
        assert obj.rekey_time == "7200"
        assert obj.uuid == "uuid-1"
