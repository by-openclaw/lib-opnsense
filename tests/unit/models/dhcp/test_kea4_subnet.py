# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.kea4_subnet — Kea4Subnet."""

from __future__ import annotations

import pytest

from opnsense.models.dhcp.kea4_subnet import Kea4Subnet


class TestKea4Subnet:
    """Kea4Subnet frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            Kea4Subnet(subnet="10.0.0.0/24").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = Kea4Subnet(subnet="10.0.0.0/24")
        assert obj.subnet == "10.0.0.0/24"

    def test_defaults(self) -> None:
        obj = Kea4Subnet(subnet="10.0.0.0/24")
        assert obj.pools == ""
        assert obj.next_server == ""
        assert obj.option_data_autocollect == "1"
        assert obj.description == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = Kea4Subnet(
            subnet="10.0.0.0/24",
            pools="10.0.0.100-10.0.0.200",
            next_server="10.0.0.1",
            option_data_autocollect="0",
            description="LAN pool",
            uuid="abc-123",
        )
        assert obj.pools == "10.0.0.100-10.0.0.200"
        assert obj.next_server == "10.0.0.1"
        assert obj.option_data_autocollect == "0"
        assert obj.description == "LAN pool"
        assert obj.uuid == "abc-123"
