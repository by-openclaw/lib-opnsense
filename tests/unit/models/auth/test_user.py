# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.auth_user — AuthUser."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from opnsense.models.auth.user import AuthUser


class TestAuthUser:
    """AuthUser frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AuthUser(name="rune").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        user = AuthUser(name="svc-test")
        assert user.name == "svc-test"

    def test_defaults(self) -> None:
        user = AuthUser(name="rune")
        assert user.email == ""
        assert user.password == ""
        assert user.disabled == "0"
        assert user.shell == ""
        assert user.expires == ""
        assert user.uuid == ""

    def test_all_fields(self) -> None:
        user = AuthUser(
            name="rune",
            email="rune@example.com",
            password="secret",
            disabled="0",
            shell="/bin/sh",
            expires="2026-12-31",
            uuid="abc-123",
        )
        assert user.email == "rune@example.com"
        assert user.shell == "/bin/sh"
        assert user.uuid == "abc-123"

    def test_asdict(self) -> None:
        user = AuthUser(name="rune")
        d = asdict(user)
        assert d["name"] == "rune"
        assert "uuid" in d
