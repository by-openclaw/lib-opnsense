# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_vti -- IpsecVti."""

from __future__ import annotations

import pytest

from opnsense.models.ipsec_vti import IpsecVti


class TestIpsecVti:
    """IpsecVti frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecVti(description="vti0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecVti(description="vti0")
        assert obj.description == "vti0"

    def test_defaults(self) -> None:
        obj = IpsecVti(description="vti0")
        assert obj.enabled == "1"
        assert obj.reqid == ""
        assert obj.local == ""
        assert obj.remote == ""
        assert obj.tunnel_local == ""
        assert obj.tunnel_remote == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecVti(
            description="vti-to-site-b",
            enabled="1",
            reqid="100",
            local="198.51.100.1",
            remote="203.0.113.1",
            tunnel_local="10.10.10.1/30",
            tunnel_remote="10.10.10.2/30",
            uuid="uuid-1",
        )
        assert obj.description == "vti-to-site-b"
        assert obj.reqid == "100"
        assert obj.local == "198.51.100.1"
        assert obj.tunnel_local == "10.10.10.1/30"
        assert obj.uuid == "uuid-1"
