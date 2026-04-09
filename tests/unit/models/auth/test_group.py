# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.auth_group — AuthGroup."""

from __future__ import annotations

import pytest

from opnsense.models.auth.group import AuthGroup


class TestAuthGroup:
    """AuthGroup frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AuthGroup(name="admins").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        group = AuthGroup(name="admins")
        assert group.name == "admins"

    def test_defaults(self) -> None:
        group = AuthGroup(name="admins")
        assert group.description == ""
        assert group.uuid == ""
