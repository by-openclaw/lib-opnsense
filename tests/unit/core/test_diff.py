# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/diff.py — DiffEngine."""

from __future__ import annotations

from opnsense.core.diff import DiffEngine

# Fixtures for the write-only (UpdateOnlyTextField) cases — fake values, never real credentials.
_PLAIN = "not-a-real-password"  # pragma: allowlist secret
_HASH = "$2y$10$" + "a" * 53  # pragma: allowlist secret
_WRITE_ONLY_KEYS = ("password", "api_key", "apikey", "psk", "secret", "bind_password", "passwd")


class TestComputeDiff:
    """compute_diff compares current vs desired state."""

    def setup_method(self) -> None:
        self.engine = DiffEngine()

    def test_identical_dicts_returns_none(self) -> None:
        current = {"name": "rune", "scope": "local"}
        desired = {"name": "rune", "scope": "local"}
        assert self.engine.compute_diff(current, desired) is None

    def test_write_only_field_returned_empty_is_not_a_diff(self) -> None:
        # OPNsense never returns UpdateOnlyTextField values from get: password == "" carries no
        # information, so a desired plaintext must not re-write the same secret on every run.
        current = {"name": "alice", "password": "", "disabled": "0"}
        desired = {"name": "alice", "password": _PLAIN, "disabled": "0"}
        assert self.engine.compute_diff(current, desired) is None

    def test_write_only_field_still_diffs_when_the_api_returns_a_hash(self) -> None:
        # a bcrypt hash that does NOT verify against the desired plaintext is real drift
        current = {"name": "alice", "password": _HASH}
        desired = {"name": "alice", "password": _PLAIN}
        assert self.engine.compute_diff(current, desired) == {"password": _PLAIN}

    def test_empty_current_value_still_diffs_for_ordinary_fields(self) -> None:
        current = {"name": "alice", "descr": ""}
        desired = {"name": "alice", "descr": "Platform admin"}
        assert self.engine.compute_diff(current, desired) == {"descr": "Platform admin"}

    def test_write_only_key_variants(self) -> None:
        for key in _WRITE_ONLY_KEYS:
            assert self.engine.compute_diff({key: ""}, {key: "x"}) is None, key
        # not write-only: a key that merely contains the letters
        assert self.engine.compute_diff({"keyboard": ""}, {"keyboard": "x"}) == {"keyboard": "x"}

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


class TestNestedDictDiff:
    """compute_diff handles nested dict comparison."""

    def setup_method(self) -> None:
        self.engine = DiffEngine()

    def test_identical_nested_dicts(self) -> None:
        current = {"options": {"dns": "10.0.0.1", "router": "10.0.0.1"}}
        desired = {"options": {"dns": "10.0.0.1", "router": "10.0.0.1"}}
        assert self.engine.compute_diff(current, desired) is None

    def test_nested_dict_with_difference(self) -> None:
        current = {"options": {"dns": "10.0.0.1", "router": "10.0.0.1"}}
        desired = {"options": {"dns": "10.0.0.2", "router": "10.0.0.1"}}
        diff = self.engine.compute_diff(current, desired)
        assert diff is not None
        assert "options" in diff

    def test_nested_dict_with_enum_normalization(self) -> None:
        """Nested enum dict (OPNsense read format) compared to flat write value."""
        current = {
            "options": {
                "dns": {"10.0.0.1": {"value": "10.0.0.1", "selected": 1}},
            }
        }
        desired = {"options": {"dns": "10.0.0.1"}}
        assert self.engine.compute_diff(current, desired) is None

    def test_nested_dict_desired_missing_from_current(self) -> None:
        """Desired has nested dict but current doesn't have that key."""
        current = {"name": "test"}
        desired = {"name": "test", "options": {"dns": "10.0.0.1"}}
        assert self.engine.compute_diff(current, desired) is None

    def test_dnat_source_destination(self) -> None:
        """D-NAT nested source/destination comparison."""
        current = {"source": {"network": "", "port": "", "not": "0"}}
        desired = {"source": {"network": "10.0.0.0/8", "not": "1"}}
        diff = self.engine.compute_diff(current, desired)
        assert diff is not None
        assert "source" in diff


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
