# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_filter — FwFilterRule."""

from __future__ import annotations

import pytest

from opnsense.models.fw_filter import FwFilterRule


class TestFwFilterRule:
    """FwFilterRule frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwFilterRule(description="block all").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        rule = FwFilterRule(description="Allow HTTPS")
        assert rule.description == "Allow HTTPS"

    def test_defaults(self) -> None:
        rule = FwFilterRule(description="test")
        assert rule.action == "pass"
        assert rule.direction == "in"
        assert rule.enabled == "1"
        assert rule.quick == "1"
        assert rule.log == "0"

    def test_composite_identity(self) -> None:
        rule = FwFilterRule(
            description="Allow HTTPS",
            interface="lan",
            direction="in",
            protocol="TCP",
        )
        assert rule.interface == "lan"
        assert rule.protocol == "TCP"
