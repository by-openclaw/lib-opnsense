# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ts_pipe — TsPipe."""

from __future__ import annotations

import pytest

from opnsense.models.ts_pipe import TsPipe


class TestTsPipe:
    """TsPipe frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            TsPipe(description="upstream").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        pipe = TsPipe(description="upstream")
        assert pipe.description == "upstream"

    def test_defaults(self) -> None:
        pipe = TsPipe(description="test")
        assert pipe.bandwidthMetric == "Mbit"
        assert pipe.enabled == "1"

    def test_bandwidth(self) -> None:
        pipe = TsPipe(description="100mbit", bandwidth="100", bandwidthMetric="Mbit")
        assert pipe.bandwidth == "100"
