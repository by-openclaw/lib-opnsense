# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ts_rule — TsRule."""

from __future__ import annotations

import pytest

from opnsense.models.shaper.ts_rule import TsRule


class TestTsRule:
    """TsRule frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            TsRule(description="shape").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        rule = TsRule(description="shape")
        assert rule.description == "shape"

    def test_defaults(self) -> None:
        rule = TsRule(description="test")
        assert rule.interface == ""
        assert rule.proto == "ip"
        assert rule.direction == ""
        assert rule.enabled == "1"
        assert rule.sequence == "1"
        assert rule.src_port == "any"
        assert rule.dst_port == "any"
        assert rule.uuid == ""

    def test_custom_values(self) -> None:
        rule = TsRule(
            description="voip",
            interface="lan",
            proto="udp",
            direction="in",
            enabled="0",
            sequence="10",
            src_port="5060",
            dst_port="5060",
            uuid="abc-123",
        )
        assert rule.interface == "lan"
        assert rule.proto == "udp"
        assert rule.direction == "in"
        assert rule.enabled == "0"
        assert rule.sequence == "10"
        assert rule.src_port == "5060"
        assert rule.dst_port == "5060"
        assert rule.uuid == "abc-123"

    def test_equality(self) -> None:
        a = TsRule(description="r1", interface="lan", proto="tcp")
        b = TsRule(description="r1", interface="lan", proto="tcp")
        assert a == b

    def test_inequality(self) -> None:
        a = TsRule(description="r1", interface="lan", proto="tcp")
        b = TsRule(description="r1", interface="wan", proto="tcp")
        assert a != b
