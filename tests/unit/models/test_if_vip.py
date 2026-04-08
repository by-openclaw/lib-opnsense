# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_vip — IfVip."""

from __future__ import annotations

import pytest

from opnsense.models.if_vip import IfVip


class TestIfVip:
    """IfVip frozen dataclass — CARP password is a field."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfVip(address="10.0.0.1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        vip = IfVip(address="10.0.0.1")
        assert vip.address == "10.0.0.1"

    def test_defaults(self) -> None:
        vip = IfVip(address="10.0.0.1")
        assert vip.mode == "ipalias"
        assert vip.password == ""

    def test_carp_mode(self) -> None:
        vip = IfVip(address="10.0.0.1", mode="carp", password="secret")
        assert vip.mode == "carp"
        assert vip.password == "secret"
