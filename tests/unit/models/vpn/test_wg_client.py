# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.wg_client — WgClient."""

from __future__ import annotations

import pytest

from opnsense.models.vpn.wg_client import WgClient


class TestWgClient:
    """WgClient frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            WgClient(name="peer0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = WgClient(name="peer0")
        assert obj.name == "peer0"

    def test_defaults(self) -> None:
        obj = WgClient(name="peer0")
        assert obj.enabled == "1"
        assert obj.pubkey == ""
        assert obj.psk == ""
        assert obj.tunneladdress == ""
        assert obj.serveraddress == ""
        assert obj.serverport == ""
        assert obj.keepalive == ""
        assert obj.uuid == ""
