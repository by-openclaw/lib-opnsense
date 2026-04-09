# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_vxlan — IfVxlan."""

from __future__ import annotations

import pytest

from opnsense.models.interfaces.vxlan import IfVxlan


class TestIfVxlan:
    """IfVxlan frozen dataclass — composite key (vxlanid + vxlanlocal)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfVxlan(vxlanid="100").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        vx = IfVxlan(vxlanid="100")
        assert vx.vxlanid == "100"

    def test_defaults(self) -> None:
        vx = IfVxlan(vxlanid="100")
        assert vx.vxlanlocal == ""
        assert vx.vxlanlocalport == ""
        assert vx.vxlanremote == ""
        assert vx.vxlanremoteport == ""
        assert vx.uuid == ""
