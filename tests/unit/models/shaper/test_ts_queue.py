# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ts_queue — TsQueue."""

from __future__ import annotations

import pytest

from opnsense.models.shaper.ts_queue import TsQueue


class TestTsQueue:
    """TsQueue frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            TsQueue(description="voip").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        queue = TsQueue(description="voip")
        assert queue.description == "voip"

    def test_defaults(self) -> None:
        queue = TsQueue(description="test")
        assert queue.weight == "100"
        assert queue.enabled == "1"
        assert queue.mask == "none"
        assert queue.codel_enable == "0"
        assert queue.uuid == ""

    def test_custom_values(self) -> None:
        queue = TsQueue(
            description="bulk",
            weight="10",
            enabled="0",
            mask="src-ip",
            codel_enable="1",
            uuid="abc-123",
        )
        assert queue.weight == "10"
        assert queue.enabled == "0"
        assert queue.mask == "src-ip"
        assert queue.codel_enable == "1"
        assert queue.uuid == "abc-123"

    def test_equality(self) -> None:
        a = TsQueue(description="q1", weight="50")
        b = TsQueue(description="q1", weight="50")
        assert a == b

    def test_inequality(self) -> None:
        a = TsQueue(description="q1", weight="50")
        b = TsQueue(description="q1", weight="60")
        assert a != b
