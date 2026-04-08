# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_source_nat — FwSourceNatRule."""

from __future__ import annotations

import pytest

from opnsense.models.fw_source_nat import FwSourceNatRule


class TestFwSourceNatRule:
    """FwSourceNatRule frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwSourceNatRule(description="masquerade").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        rule = FwSourceNatRule(description="masquerade")
        assert rule.description == "masquerade"

    def test_defaults(self) -> None:
        rule = FwSourceNatRule(description="test")
        assert rule.enabled == "1"
        assert rule.ipprotocol == "inet"
