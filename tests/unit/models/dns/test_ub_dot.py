# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ub_dot — UbDot."""

from __future__ import annotations

import pytest

from opnsense.models.dns.ub_dot import UbDot


class TestUbDot:
    """UbDot frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            UbDot(server="1.1.1.1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = UbDot(server="1.1.1.1")
        assert obj.server == "1.1.1.1"

    def test_defaults(self) -> None:
        obj = UbDot(server="1.1.1.1")
        assert obj.port == "853"
        assert obj.type == "dot"
        assert obj.forward_tcp_upstream == "0"
        assert obj.forward_first == "0"
        assert obj.enabled == "1"
        assert obj.uuid == ""
