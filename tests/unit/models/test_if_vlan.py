# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_vlan — IfVlan."""

from __future__ import annotations

import pytest

from opnsense.models.if_vlan import IfVlan


class TestIfVlan:
    """IfVlan frozen dataclass — composite key (tag + if)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfVlan(tag="100").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        vlan = IfVlan(tag="100")
        assert vlan.tag == "100"

    def test_defaults(self) -> None:
        vlan = IfVlan(tag="100")
        assert vlan.if_ == ""
        assert vlan.pcp == ""
        assert vlan.descr == ""
