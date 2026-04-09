# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_gre — IfGre."""

from __future__ import annotations

import pytest

from opnsense.models.interfaces.gre import IfGre


class TestIfGre:
    """IfGre frozen dataclass — composite key (tunnel-local-addr + tunnel-remote-addr)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfGre(tunnel_local_addr="10.0.0.1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        gre = IfGre(tunnel_local_addr="10.0.0.1")
        assert gre.tunnel_local_addr == "10.0.0.1"

    def test_defaults(self) -> None:
        gre = IfGre(tunnel_local_addr="10.0.0.1")
        assert gre.tunnel_remote_addr == ""
        assert gre.tunnel_remote_net == "32"
        assert gre.descr == ""
        assert gre.uuid == ""
