# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.cp_zone — CpZone."""

from __future__ import annotations

import pytest

from opnsense.models.cp_zone import CpZone


class TestCpZone:
    """CpZone frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            CpZone(description="Guest WiFi").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = CpZone(description="Guest WiFi")
        assert obj.description == "Guest WiFi"

    def test_defaults(self) -> None:
        obj = CpZone(description="Guest WiFi")
        assert obj.enabled == "1"
        assert obj.interfaces == ""
        assert obj.authservers == ""
        assert obj.idletimeout == "0"
        assert obj.hardtimeout == "0"
        assert obj.concurrentlogins == "1"
        assert obj.certificate == ""
        assert obj.servername == ""
        assert obj.uuid == ""
