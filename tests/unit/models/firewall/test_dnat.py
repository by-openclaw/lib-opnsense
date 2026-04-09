# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.fw_dnat — FwDnatRule."""

from __future__ import annotations

import pytest

from opnsense.models.firewall.dnat import FwDnatRule


class TestFwDnatRule:
    """FwDnatRule frozen dataclass — uses 'descr' not 'description'."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FwDnatRule(descr="port forward").uuid = "changed"  # type: ignore[misc]

    def test_descr_field(self) -> None:
        rule = FwDnatRule(descr="port forward 443")
        assert rule.descr == "port forward 443"

    def test_defaults(self) -> None:
        rule = FwDnatRule(descr="test")
        assert rule.disabled == "0"
        assert rule.ipprotocol == "inet"
