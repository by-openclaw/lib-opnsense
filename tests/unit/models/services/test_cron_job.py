# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.cron_job — CronJob."""

from __future__ import annotations

import pytest

from opnsense.models.cron_job import CronJob


class TestCronJob:
    """CronJob frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            CronJob(description="Test job").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = CronJob(description="Test job")
        assert obj.description == "Test job"

    def test_defaults(self) -> None:
        obj = CronJob(description="Test job")
        assert obj.enabled == "1"
        assert obj.minutes == "0"
        assert obj.hours == "0"
        assert obj.days == "*"
        assert obj.months == "*"
        assert obj.weekdays == "*"
        assert obj.command == ""
        assert obj.who == "root"
        assert obj.parameters == ""
        assert obj.uuid == ""
