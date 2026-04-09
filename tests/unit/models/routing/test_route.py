# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.rt_route -- RtRoute."""

from __future__ import annotations

import pytest

from opnsense.models.routing.route import RtRoute


class TestRtRoute:
    """RtRoute frozen dataclass -- composite key (network + gateway)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            RtRoute(network="10.0.0.0/8").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        route = RtRoute(network="10.0.0.0/8")
        assert route.network == "10.0.0.0/8"

    def test_defaults(self) -> None:
        route = RtRoute(network="10.0.0.0/8")
        assert route.gateway == ""
        assert route.descr == ""
        assert route.disabled == "0"
        assert route.uuid == ""
