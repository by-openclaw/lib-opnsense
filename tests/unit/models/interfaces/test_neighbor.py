# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_neighbor — IfNeighbor."""

from __future__ import annotations

import pytest

from opnsense.models.if_neighbor import IfNeighbor


class TestIfNeighbor:
    """IfNeighbor frozen dataclass — composite key (ipaddress + etheraddr)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfNeighbor(ipaddress="10.0.0.1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        nb = IfNeighbor(ipaddress="10.0.0.1")
        assert nb.ipaddress == "10.0.0.1"

    def test_defaults(self) -> None:
        nb = IfNeighbor(ipaddress="10.0.0.1")
        assert nb.etheraddr == ""
        assert nb.descr == ""
        assert nb.uuid == ""
