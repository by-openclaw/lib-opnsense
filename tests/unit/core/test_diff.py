# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/diff.py — DiffEngine."""

from __future__ import annotations

from opnsense.core.diff import DiffEngine


class TestComputeDiff:
    """compute_diff compares current vs desired state."""

    def setup_method(self) -> None:
        self.engine = DiffEngine()

    def test_identical_dicts_returns_none(self) -> None:
        current = {"name": "rune", "scope": "local"}
        desired = {"name": "rune", "scope": "local"}
        assert self.engine.compute_diff(current, desired) is None

    def test_single_field_difference(self) -> None:
        current = {"name": "rune", "scope": "local"}
        desired = {"name": "rune", "scope": "remote"}
        diff = self.engine.compute_diff(current, desired)
        assert diff == {"scope": "remote"}

    def test_fields_missing_from_current_are_skipped(self) -> None:
        current = {"name": "rune"}
        desired = {"name": "rune", "email": "rune@example.com"}
        assert self.engine.compute_diff(current, desired) is None

    def test_extra_fields_in_current_are_ignored(self) -> None:
        current = {"name": "rune", "scope": "local", "extra": "data"}
        desired = {"name": "rune", "scope": "local"}
        assert self.engine.compute_diff(current, desired) is None

    def test_enum_dict_selected_format(self) -> None:
        """Format 1: {"selected": "1"} normalizes to "1"."""
        current = {"enabled": {"selected": "1"}}
        desired = {"enabled": "1"}
        assert self.engine.compute_diff(current, desired) is None

    def test_enum_dict_selected_detects_diff(self) -> None:
        current = {"enabled": {"selected": "1"}}
        desired = {"enabled": "0"}
        diff = self.engine.compute_diff(current, desired)
        assert diff == {"enabled": "0"}

    def test_enum_dict_option_format(self) -> None:
        """Format 2: {"local": {"value": "Local", "selected": 1}} normalizes to "local"."""
        current = {
            "scope": {
                "local": {"value": "Local", "selected": 1},
                "remote": {"value": "Remote", "selected": 0},
            }
        }
        desired = {"scope": "local"}
        assert self.engine.compute_diff(current, desired) is None

    def test_enum_dict_option_format_detects_diff(self) -> None:
        current = {
            "scope": {
                "local": {"value": "Local", "selected": 1},
                "remote": {"value": "Remote", "selected": 0},
            }
        }
        desired = {"scope": "remote"}
        diff = self.engine.compute_diff(current, desired)
        assert diff == {"scope": "remote"}

    def test_current_value_none_but_key_present(self) -> None:
        """Field present in current with None value — still compared."""
        current = {"name": None}
        desired = {"name": "rune"}
        diff = self.engine.compute_diff(current, desired)
        assert diff == {"name": "rune"}

    def test_multiple_differences(self) -> None:
        current = {"name": "rune", "scope": "local", "enabled": "1"}
        desired = {"name": "youssef", "scope": "remote", "enabled": "1"}
        diff = self.engine.compute_diff(current, desired)
        assert diff == {"name": "youssef", "scope": "remote"}


class TestNormalizeValue:
    """normalize_value handles OPNsense enum dict formats."""

    def test_plain_string(self) -> None:
        assert DiffEngine.normalize_value("hello") == "hello"

    def test_integer(self) -> None:
        assert DiffEngine.normalize_value(42) == "42"

    def test_selected_dict(self) -> None:
        assert DiffEngine.normalize_value({"selected": "1"}) == "1"

    def test_option_dict(self) -> None:
        val = {"lan": {"value": "LAN", "selected": 1}, "wan": {"value": "WAN", "selected": 0}}
        assert DiffEngine.normalize_value(val) == "lan"

    def test_option_dict_string_selected(self) -> None:
        val = {"lan": {"value": "LAN", "selected": "1"}, "wan": {"value": "WAN", "selected": "0"}}
        assert DiffEngine.normalize_value(val) == "lan"

    def test_option_dict_bool_selected(self) -> None:
        val = {
            "lan": {"value": "LAN", "selected": True},
            "wan": {"value": "WAN", "selected": False},
        }
        assert DiffEngine.normalize_value(val) == "lan"
