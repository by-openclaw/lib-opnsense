# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ub_host_alias — UbHostAlias."""

from __future__ import annotations

import pytest

from opnsense.models.ub_host_alias import UbHostAlias


class TestUbHostAlias:
    """UbHostAlias frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            UbHostAlias(hostname="web-alias").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = UbHostAlias(hostname="web-alias")
        assert obj.hostname == "web-alias"

    def test_defaults(self) -> None:
        obj = UbHostAlias(hostname="web-alias")
        assert obj.domain == ""
        assert obj.host == ""
        assert obj.enabled == "1"
        assert obj.description == ""
        assert obj.uuid == ""

    def test_missing_hostname_raises(self) -> None:
        with pytest.raises(TypeError):
            UbHostAlias()  # type: ignore[call-arg]
