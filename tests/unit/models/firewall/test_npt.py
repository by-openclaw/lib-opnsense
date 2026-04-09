# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_npt -- FwNptRule."""

from __future__ import annotations

import pytest

from opnsense.models.firewall.npt import FwNptRule


class TestFwNptRule:
    """FwNptRule frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwNptRule(source_net="fd00:1::/64").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        rule = FwNptRule(source_net="fd00:1::/64")
        assert rule.source_net == "fd00:1::/64"

    def test_defaults(self) -> None:
        rule = FwNptRule(source_net="fd00:1::/64")
        assert rule.enabled == "1"
        assert rule.log == "0"
        assert rule.sequence == "100"
        assert rule.description == ""
        assert rule.destination_net == ""
        assert rule.interface == ""
        assert rule.uuid == ""
