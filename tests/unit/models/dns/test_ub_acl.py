# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ub_acl — UbAcl."""

from __future__ import annotations

import pytest

from opnsense.models.dns.ub_acl import UbAcl


class TestUbAcl:
    """UbAcl frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            UbAcl(name="lan-access").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = UbAcl(name="lan-access")
        assert obj.name == "lan-access"

    def test_defaults(self) -> None:
        obj = UbAcl(name="lan-access")
        assert obj.action == "allow"
        assert obj.enabled == "1"
        assert obj.networks == ""
        assert obj.uuid == ""
