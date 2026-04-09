# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_lagg — IfLagg."""

from __future__ import annotations

import pytest

from opnsense.models.if_lagg import IfLagg


class TestIfLagg:
    """IfLagg frozen dataclass — single key (descr)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfLagg(descr="bond0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        lagg = IfLagg(descr="bond0")
        assert lagg.descr == "bond0"

    def test_defaults(self) -> None:
        lagg = IfLagg(descr="bond0")
        assert lagg.members == ""
        assert lagg.proto == "lacp"
        assert lagg.lacp_fast_timeout == "0"
        assert lagg.mtu == ""
        assert lagg.uuid == ""
