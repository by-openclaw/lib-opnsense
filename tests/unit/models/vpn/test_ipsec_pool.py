# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_pool -- IpsecPool."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.ipsec_pool import IpsecPool


class TestIpsecPool:
    """IpsecPool frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecPool(name="pool0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecPool(name="pool0")
        assert obj.name == "pool0"

    def test_defaults(self) -> None:
        obj = IpsecPool(name="pool0")
        assert obj.enabled == "1"
        assert obj.addrs == ""
        assert obj.dns == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecPool(
            name="roadwarrior-pool",
            enabled="1",
            addrs="10.10.10.0/24",
            dns="10.10.10.1",
            uuid="uuid-1",
        )
        assert obj.name == "roadwarrior-pool"
        assert obj.addrs == "10.10.10.0/24"
        assert obj.dns == "10.10.10.1"
        assert obj.uuid == "uuid-1"
