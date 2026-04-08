# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_bridge — IfBridge."""

from __future__ import annotations

import pytest

from opnsense.models.if_bridge import IfBridge


class TestIfBridge:
    """IfBridge frozen dataclass — single key (descr)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfBridge(descr="br0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        bridge = IfBridge(descr="br0")
        assert bridge.descr == "br0"

    def test_defaults(self) -> None:
        bridge = IfBridge(descr="br0")
        assert bridge.members == ""
        assert bridge.linklocal == "0"
        assert bridge.enablestp == "0"
        assert bridge.proto == "rstp"
        assert bridge.uuid == ""
