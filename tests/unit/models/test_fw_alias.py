# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_alias — FwAlias."""

from __future__ import annotations

import pytest

from opnsense.models.fw_alias import FwAlias


class TestFwAlias:
    """FwAlias frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwAlias(name="trusted").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        alias = FwAlias(name="trusted_hosts")
        assert alias.name == "trusted_hosts"

    def test_defaults(self) -> None:
        alias = FwAlias(name="test")
        assert alias.type == "host"
        assert alias.enabled == "1"
        assert alias.content == ""
