# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_psk -- IpsecPsk."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.ipsec_psk import IpsecPsk


class TestIpsecPsk:
    """IpsecPsk frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecPsk(description="psk0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecPsk(description="psk0")
        assert obj.description == "psk0"

    def test_defaults(self) -> None:
        obj = IpsecPsk(description="psk0")
        assert obj.ident == ""
        assert obj.remote_ident == ""
        assert obj.keyType == "PSK"
        assert obj.Key == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecPsk(
            description="site-a-psk",
            ident="site-a.example.com",
            remote_ident="site-b.example.com",
            keyType="PSK",
            Key="supersecret",
            uuid="uuid-1",
        )
        assert obj.description == "site-a-psk"
        assert obj.ident == "site-a.example.com"
        assert obj.Key == "supersecret"
        assert obj.uuid == "uuid-1"
