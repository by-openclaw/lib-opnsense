# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_loopback — IfLoopback."""

from __future__ import annotations

import pytest

from opnsense.models.if_loopback import IfLoopback


class TestIfLoopback:
    """IfLoopback frozen dataclass — single key (description)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfLoopback(description="lo0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        lo = IfLoopback(description="lo0")
        assert lo.description == "lo0"

    def test_defaults(self) -> None:
        lo = IfLoopback(description="lo0")
        assert lo.deviceId == ""
        assert lo.uuid == ""
