# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/logging_helpers.py — ManagerLogBuilder."""

from __future__ import annotations

from opnsense.core.logging_helpers import ACTION_SEVERITY, ManagerLogBuilder


class TestSeverityMapping:
    """severity() maps action to correct log level."""

    def test_created_is_info(self) -> None:
        assert ManagerLogBuilder.severity("created") == "info"

    def test_updated_is_info(self) -> None:
        assert ManagerLogBuilder.severity("updated") == "info"

    def test_deleted_is_warning(self) -> None:
        assert ManagerLogBuilder.severity("deleted") == "warning"

    def test_noop_is_debug(self) -> None:
        assert ManagerLogBuilder.severity("noop") == "debug"

    def test_failures_are_error(self) -> None:
        for action in [
            "create_failed",
            "update_failed",
            "delete_failed",
            "list_failed",
            "get_failed",
            "apply_failed",
            "ambiguous_match",
            "validation_failed",
        ]:
            assert ManagerLogBuilder.severity(action) == "error", f"{action} should be error"

    def test_unknown_defaults_to_info(self) -> None:
        assert ManagerLogBuilder.severity("unknown_action") == "info"


class TestDurationMs:
    """duration_ms calculates elapsed time."""

    def test_returns_float(self) -> None:
        builder = ManagerLogBuilder()
        ms = builder.duration_ms()
        assert isinstance(ms, float)
        assert ms >= 0.0


class TestBuildExtra:
    """build_extra produces correct structured dicts."""

    def test_created_with_all_fields(self) -> None:
        builder = ManagerLogBuilder()
        match_fields = {"match_keys": {"name": "rune"}, "endpoint": "auth/user"}
        extra = builder.build_extra(
            "created",
            match_fields,
            uuid="abc-123",
            after={"name": "rune"},
            changed=True,
        )
        assert extra["action"] == "created"
        assert extra["uuid"] == "abc-123"
        assert extra["changed"] is True
        assert extra["after"] == {"name": "rune"}
        assert extra["match_keys"] == {"name": "rune"}
        assert extra["endpoint"] == "auth/user"
        assert "duration_ms" in extra
        assert "before" not in extra

    def test_noop_minimal_fields(self) -> None:
        builder = ManagerLogBuilder()
        extra = builder.build_extra("noop", changed=False)
        assert extra["action"] == "noop"
        assert extra["changed"] is False
        assert "duration_ms" in extra
        assert "uuid" not in extra
        assert "before" not in extra
        assert "after" not in extra

    def test_error_with_message(self) -> None:
        builder = ManagerLogBuilder()
        extra = builder.build_extra(
            "create_failed",
            error="Connection refused",
        )
        assert extra["action"] == "create_failed"
        assert extra["error"] == "Connection refused"
        assert "duration_ms" in extra

    def test_check_mode_included(self) -> None:
        builder = ManagerLogBuilder()
        extra = builder.build_extra("created", check_mode=True, changed=True)
        assert extra["check_mode"] is True

    def test_before_and_after(self) -> None:
        builder = ManagerLogBuilder()
        extra = builder.build_extra(
            "updated",
            before={"scope": "local"},
            after={"scope": "remote"},
            changed=True,
        )
        assert extra["before"] == {"scope": "local"}
        assert extra["after"] == {"scope": "remote"}

    def test_duration_ms_always_present(self) -> None:
        builder = ManagerLogBuilder()
        extra = builder.build_extra("noop")
        assert "duration_ms" in extra
        assert isinstance(extra["duration_ms"], float)


class TestActionSeverityCompleteness:
    """ACTION_SEVERITY covers all documented actions."""

    def test_all_actions_mapped(self) -> None:
        expected = {
            "created",
            "updated",
            "deleted",
            "noop",
            "create_failed",
            "update_failed",
            "delete_failed",
            "list_failed",
            "get_failed",
            "get_schema_failed",
            "apply_failed",
            "ambiguous_match",
            "validation_failed",
        }
        assert set(ACTION_SEVERITY.keys()) == expected
