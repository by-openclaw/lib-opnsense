# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.kea4_peer — Kea4Peer."""

from __future__ import annotations

import pytest

from opnsense.models.dhcp.kea4_peer import Kea4Peer


class TestKea4Peer:
    """Kea4Peer frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            Kea4Peer(name="peer-standby").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = Kea4Peer(name="peer-standby")
        assert obj.name == "peer-standby"

    def test_defaults(self) -> None:
        obj = Kea4Peer(name="peer-standby")
        assert obj.role == "primary"
        assert obj.url == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = Kea4Peer(
            name="peer-standby",
            role="standby",
            url="https://peer.example.com:8000/",
            uuid="abc-123",
        )
        assert obj.role == "standby"
        assert obj.url == "https://peer.example.com:8000/"
        assert obj.uuid == "abc-123"
