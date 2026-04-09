# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_local -- IpsecLocal."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.ipsec_local import IpsecLocal


class TestIpsecLocal:
    """IpsecLocal frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecLocal(description="local0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecLocal(description="local0")
        assert obj.description == "local0"

    def test_defaults(self) -> None:
        obj = IpsecLocal(description="local0")
        assert obj.enabled == "1"
        assert obj.connection == ""
        assert obj.auth == ""
        assert obj.id == ""
        assert obj.eap_id == ""
        assert obj.round == "0"
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecLocal(
            description="local-psk",
            enabled="1",
            connection="conn-uuid-1",
            auth="psk",
            id="site-a.example.com",
            eap_id="user@example.com",
            round="0",
            uuid="uuid-1",
        )
        assert obj.description == "local-psk"
        assert obj.auth == "psk"
        assert obj.id == "site-a.example.com"
        assert obj.uuid == "uuid-1"
