# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_one_to_one — FwOneToOneRule."""

from __future__ import annotations

import pytest

from opnsense.models.fw_one_to_one import FwOneToOneRule


class TestFwOneToOneRule:
    """FwOneToOneRule frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwOneToOneRule(description="1to1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        rule = FwOneToOneRule(description="1to1 nat")
        assert rule.description == "1to1 nat"

    def test_defaults(self) -> None:
        rule = FwOneToOneRule(description="test")
        assert rule.disabled == "0"
