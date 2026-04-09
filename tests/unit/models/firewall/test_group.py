# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_group — FwGroup."""

from __future__ import annotations

import pytest

from opnsense.models.firewall.group import FwGroup


class TestFwGroup:
    """FwGroup frozen dataclass — uses 'ifname' as identity."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwGroup(ifname="grp0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        grp = FwGroup(ifname="trusted_if")
        assert grp.ifname == "trusted_if"

    def test_defaults(self) -> None:
        grp = FwGroup(ifname="grp0")
        assert grp.members == ""
        assert grp.descr == ""
