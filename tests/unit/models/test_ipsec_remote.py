# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_remote -- IpsecRemote."""

from __future__ import annotations

import pytest

from opnsense.models.ipsec_remote import IpsecRemote


class TestIpsecRemote:
    """IpsecRemote frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecRemote(description="remote0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecRemote(description="remote0")
        assert obj.description == "remote0"

    def test_defaults(self) -> None:
        obj = IpsecRemote(description="remote0")
        assert obj.enabled == "1"
        assert obj.connection == ""
        assert obj.auth == ""
        assert obj.id == ""
        assert obj.eap_id == ""
        assert obj.round == "0"
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecRemote(
            description="remote-psk",
            enabled="1",
            connection="conn-uuid-1",
            auth="psk",
            id="site-b.example.com",
            eap_id="peer@example.com",
            round="0",
            uuid="uuid-1",
        )
        assert obj.description == "remote-psk"
        assert obj.auth == "psk"
        assert obj.id == "site-b.example.com"
        assert obj.uuid == "uuid-1"
