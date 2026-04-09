# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_category — FwCategory."""

from __future__ import annotations

import pytest

from opnsense.models.firewall.category import FwCategory


class TestFwCategory:
    """FwCategory frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwCategory(name="web").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        cat = FwCategory(name="web")
        assert cat.name == "web"

    def test_color(self) -> None:
        cat = FwCategory(name="web", color="ff0000")
        assert cat.color == "ff0000"
