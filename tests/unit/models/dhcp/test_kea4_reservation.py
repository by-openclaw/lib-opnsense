# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.kea4_reservation — Kea4Reservation."""

from __future__ import annotations

import pytest

from opnsense.models.dhcp.kea4_reservation import Kea4Reservation


class TestKea4Reservation:
    """Kea4Reservation frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            Kea4Reservation(ip_address="10.0.0.50").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = Kea4Reservation(ip_address="10.0.0.50")
        assert obj.ip_address == "10.0.0.50"

    def test_defaults(self) -> None:
        obj = Kea4Reservation(ip_address="10.0.0.50")
        assert obj.hw_address == ""
        assert obj.hostname == ""
        assert obj.description == ""
        assert obj.uuid == ""

    def test_composite_identity(self) -> None:
        obj = Kea4Reservation(
            ip_address="10.0.0.50",
            hw_address="00:11:22:33:44:55",
            hostname="printer",
        )
        assert obj.hw_address == "00:11:22:33:44:55"
        assert obj.hostname == "printer"
