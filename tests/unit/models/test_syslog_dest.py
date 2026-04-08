# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.syslog_dest — SyslogDest."""

from __future__ import annotations

import pytest

from opnsense.models.syslog_dest import SyslogDest


class TestSyslogDest:
    """SyslogDest frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            SyslogDest(description="central").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        dest = SyslogDest(description="central")
        assert dest.description == "central"

    def test_defaults(self) -> None:
        dest = SyslogDest(description="test")
        assert dest.enabled == "1"
        assert dest.transport == "udp4"
        assert dest.port == "514"
        assert dest.rfc5424 == "0"
        assert dest.program == ""
        assert dest.level == ""
        assert dest.facility == ""
        assert dest.hostname == ""
        assert dest.certificate == ""
        assert dest.uuid == ""

    def test_all_fields(self) -> None:
        dest = SyslogDest(
            description="central syslog",
            enabled="1",
            transport="tcp4",
            program="nginx",
            level="err,crit",
            facility="local0",
            hostname="syslog.example.com",
            port="1514",
            rfc5424="1",
            certificate="cert-ref",
            uuid="uuid-1",
        )
        assert dest.description == "central syslog"
        assert dest.transport == "tcp4"
        assert dest.hostname == "syslog.example.com"
        assert dest.port == "1514"
        assert dest.rfc5424 == "1"
