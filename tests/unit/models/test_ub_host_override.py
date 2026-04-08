# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ub_host_override — UbHostOverride."""

from __future__ import annotations

import pytest

from opnsense.models.ub_host_override import UbHostOverride


class TestUbHostOverride:
    """UbHostOverride frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            UbHostOverride(hostname="ns1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = UbHostOverride(hostname="ns1")
        assert obj.hostname == "ns1"

    def test_defaults(self) -> None:
        obj = UbHostOverride(hostname="ns1")
        assert obj.rr == "A"
        assert obj.addptr == "1"
        assert obj.enabled == "1"
        assert obj.domain == ""
        assert obj.server == ""
        assert obj.uuid == ""
