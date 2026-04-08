# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ddns_account — DdnsAccount."""

from __future__ import annotations

import pytest

from opnsense.models.ddns_account import DdnsAccount


class TestDdnsAccount:
    """DdnsAccount frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            DdnsAccount(description="test").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        account = DdnsAccount(description="cloudflare ddns")
        assert account.description == "cloudflare ddns"

    def test_defaults(self) -> None:
        account = DdnsAccount(description="test")
        assert account.enabled == "1"
        assert account.service == "cloudflare"
        assert account.protocol == ""
        assert account.server == ""
        assert account.username == ""
        assert account.password == ""
        assert account.resourceId == ""
        assert account.zone == ""
        assert account.wildcard == "0"
        assert account.checkip == "web_cloudflare"
        assert account.checkip_timeout == "10"
        assert account.force_ssl == "1"
        assert account.ttl == "300"
        assert account.interface == ""
        assert account.uuid == ""

    def test_all_fields(self) -> None:
        account = DdnsAccount(
            description="Cloudflare DDNS",
            enabled="1",
            service="cloudflare",
            protocol="dyndns2",
            server="api.cloudflare.com",
            username="user@example.com",
            password="secret-token",
            resourceId="zone-id-123",
            zone="example.com",
            wildcard="1",
            checkip="web_cloudflare",
            checkip_timeout="30",
            force_ssl="1",
            ttl="300",
            interface="wan",
            uuid="uuid-1",
        )
        assert account.description == "Cloudflare DDNS"
        assert account.service == "cloudflare"
        assert account.username == "user@example.com"
        assert account.zone == "example.com"
        assert account.wildcard == "1"
        assert account.interface == "wan"
