# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/redaction.py — Redactor."""

from __future__ import annotations

from opnsense.core.redaction import DEFAULT_RULES, Redactor


class TestRedactValue:
    """redact_value applies configurable reveal depth."""

    def setup_method(self) -> None:
        self.redactor = Redactor()

    def test_full_redaction(self) -> None:
        """(0, 0) replaces entire value."""
        result = self.redactor.redact_value("password", "supersecret")
        assert result == "<REDACTED:password>"

    def test_partial_reveal_end(self) -> None:
        """(0, 4) reveals last 4 chars."""
        result = self.redactor.redact_value("secret", "mysecretvalue123")
        assert result.endswith("e123")
        assert result.startswith("*")

    def test_partial_reveal_start_and_end(self) -> None:
        """(4, 4) reveals first 4 + last 4."""
        result = self.redactor.redact_value("api_key", "gTCJxxxxxxxxxxxxigCn")
        assert result.startswith("gTCJ")
        assert result.endswith("igCn")

    def test_partial_reveal_start_only(self) -> None:
        """(8, 0) reveals first 8 chars."""
        result = self.redactor.redact_value("authorizedkeys", "ssh-ed25519AAAA...")
        assert result.startswith("ssh-ed25")
        assert "*" in result

    def test_value_shorter_than_window_fully_redacted(self) -> None:
        result = self.redactor.redact_value("api_key", "abc")
        assert result == "<REDACTED:api_key>"

    def test_field_not_in_rules_passes_through(self) -> None:
        result = self.redactor.redact_value("name", "rune")
        assert result == "rune"

    def test_non_string_value_fully_redacted(self) -> None:
        result = self.redactor.redact_value("password", 12345)
        assert result == "<REDACTED:password>"

    def test_empty_string_fully_redacted(self) -> None:
        result = self.redactor.redact_value("password", "")
        assert result == "<REDACTED:password>"

    def test_longest_match_wins(self) -> None:
        """'scrambled_password' matches 'password' (longer) over partial patterns."""
        result = self.redactor.redact_value("scrambled_password", "hashed_stuff")
        assert result == "<REDACTED:scrambled_password>"

    def test_case_insensitive_match(self) -> None:
        result = self.redactor.redact_value("Password", "secret123")
        assert result == "<REDACTED:Password>"


class TestRedactDict:
    """redact_dict deep-copies and redacts."""

    def setup_method(self) -> None:
        self.redactor = Redactor()

    def test_with_redact_fields_set(self) -> None:
        data = {"name": "rune", "password": "secret", "email": "rune@example.com"}
        result = self.redactor.redact_dict(data, redact_fields={"password"})
        assert result["name"] == "rune"
        assert result["password"] == "<REDACTED:password>"
        assert result["email"] == "rune@example.com"

    def test_deep_copies_original(self) -> None:
        data = {"name": "rune", "password": "secret"}
        result = self.redactor.redact_dict(data, redact_fields={"password"})
        assert data["password"] == "secret"
        assert result["password"] == "<REDACTED:password>"

    def test_without_redact_fields_uses_rules(self) -> None:
        data = {"name": "rune", "password": "secret123"}
        result = self.redactor.redact_dict(data)
        assert result["name"] == "rune"
        assert result["password"] == "<REDACTED:password>"

    def test_empty_redact_fields(self) -> None:
        data = {"name": "rune", "password": "secret"}
        result = self.redactor.redact_dict(data, redact_fields=set())
        assert result["password"] == "secret"


class TestCustomRules:
    """Redactor accepts custom rules."""

    def test_custom_rules(self) -> None:
        redactor = Redactor(rules={"token": (0, 0, "*")})
        assert redactor.redact_value("token", "abc123") == "<REDACTED:token>"
        assert redactor.redact_value("password", "abc123") == "abc123"

    def test_rules_property(self) -> None:
        redactor = Redactor()
        assert redactor.rules == DEFAULT_RULES


class TestStructlogProcessor:
    """structlog_processor redacts event dict fields."""

    def test_redacts_sensitive_fields(self) -> None:
        redactor = Redactor()
        event = {"msg": "created user", "password": "secret", "name": "rune"}
        result = redactor.structlog_processor(None, "info", event)
        assert result["password"] == "<REDACTED:password>"
        assert result["name"] == "rune"
        assert result["msg"] == "created user"
