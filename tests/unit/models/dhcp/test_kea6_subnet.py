# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.kea6_subnet — Kea6Subnet."""

from __future__ import annotations

import pytest

from opnsense.models.dhcp.kea6_subnet import Kea6Subnet


class TestKea6Subnet:
    """Kea6Subnet frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            Kea6Subnet(subnet="2001:db8::/64").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = Kea6Subnet(subnet="2001:db8::/64")
        assert obj.subnet == "2001:db8::/64"

    def test_defaults(self) -> None:
        obj = Kea6Subnet(subnet="2001:db8::/64")
        assert obj.description == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = Kea6Subnet(
            subnet="2001:db8::/64",
            description="IPv6 LAN pool",
            uuid="abc-123",
        )
        assert obj.description == "IPv6 LAN pool"
        assert obj.uuid == "abc-123"
