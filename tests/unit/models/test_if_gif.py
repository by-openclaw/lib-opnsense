# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.if_gif — IfGif."""

from __future__ import annotations

import pytest

from opnsense.models.if_gif import IfGif


class TestIfGif:
    """IfGif frozen dataclass — composite key (tunnel-local-addr + tunnel-remote-addr)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IfGif(tunnel_local_addr="10.0.0.1").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        gif = IfGif(tunnel_local_addr="10.0.0.1")
        assert gif.tunnel_local_addr == "10.0.0.1"

    def test_defaults(self) -> None:
        gif = IfGif(tunnel_local_addr="10.0.0.1")
        assert gif.tunnel_remote_addr == ""
        assert gif.tunnel_remote_net == "32"
        assert gif.descr == ""
        assert gif.uuid == ""
