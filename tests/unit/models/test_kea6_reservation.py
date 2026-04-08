# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.kea6_reservation — Kea6Reservation."""

from __future__ import annotations

import pytest

from opnsense.models.kea6_reservation import Kea6Reservation


class TestKea6Reservation:
    """Kea6Reservation frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            Kea6Reservation(ip_address="2001:db8::50").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = Kea6Reservation(ip_address="2001:db8::50")
        assert obj.ip_address == "2001:db8::50"

    def test_defaults(self) -> None:
        obj = Kea6Reservation(ip_address="2001:db8::50")
        assert obj.duid == ""
        assert obj.hw_address == ""
        assert obj.hostname == ""
        assert obj.description == ""
        assert obj.uuid == ""

    def test_composite_identity(self) -> None:
        obj = Kea6Reservation(
            ip_address="2001:db8::50",
            duid="00:03:00:01:00:11:22:33:44:55",
            hostname="printer",
        )
        assert obj.duid == "00:03:00:01:00:11:22:33:44:55"
        assert obj.hostname == "printer"
