# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ub_forward — UbForward."""

from __future__ import annotations

import pytest

from opnsense.models.ub_forward import UbForward


class TestUbForward:
    """UbForward frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            UbForward(domain="example.com").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = UbForward(domain="example.com")
        assert obj.domain == "example.com"

    def test_defaults(self) -> None:
        obj = UbForward(domain="example.com")
        assert obj.type == "forward"
        assert obj.forward_tcp_upstream == "0"
        assert obj.forward_first == "0"
        assert obj.enabled == "1"
        assert obj.server == ""
        assert obj.uuid == ""
