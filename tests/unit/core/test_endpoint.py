# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/endpoint.py — EndpointConfig + EndpointResolver."""

from __future__ import annotations

import pytest

from opnsense.core.endpoint import EndpointConfig, EndpointResolver


class TestEndpointConfig:
    """EndpointConfig is a frozen dataclass with auto-suffix."""

    def test_explicit_suffix(self) -> None:
        config = EndpointConfig(base="firewall/filter", payload_key="rule", entity_suffix="Rule")
        assert config.suffix == "Rule"

    def test_auto_suffix_from_payload_key(self) -> None:
        config = EndpointConfig(base="firewall/filter", payload_key="rule")
        assert config.suffix == "Rule"

    def test_empty_suffix(self) -> None:
        """Auth uses bare action names (search, not searchUser)."""
        config = EndpointConfig(base="auth/user", payload_key="user", entity_suffix="")
        assert config.suffix == ""

    def test_frozen(self) -> None:
        config = EndpointConfig(base="auth/user", payload_key="user")
        with pytest.raises(AttributeError):
            config.base = "changed"  # type: ignore[misc]


class TestEndpointResolver:
    """EndpointResolver constructs correct URLs."""

    def setup_method(self) -> None:
        self.config = EndpointConfig(
            base="firewall/filter",
            payload_key="rule",
            entity_suffix="Rule",
            apply_endpoint="firewall/filter/apply",
        )
        self.resolver = EndpointResolver(self.config)

    def test_search(self) -> None:
        assert self.resolver.search() == "firewall/filter/searchRule"

    def test_get_with_uuid(self) -> None:
        assert self.resolver.get("abc-123") == "firewall/filter/getRule/abc-123"

    def test_get_schema(self) -> None:
        assert self.resolver.get() == "firewall/filter/getRule"

    def test_add(self) -> None:
        assert self.resolver.add() == "firewall/filter/addRule"

    def test_set(self) -> None:
        assert self.resolver.set() == "firewall/filter/setRule"

    def test_delete(self) -> None:
        assert self.resolver.delete() == "firewall/filter/delRule"

    def test_apply(self) -> None:
        assert self.resolver.apply() == "firewall/filter/apply"

    def test_apply_none_for_auth(self) -> None:
        config = EndpointConfig(base="auth/user", payload_key="user", entity_suffix="")
        resolver = EndpointResolver(config)
        assert resolver.apply() is None

    def test_config_property(self) -> None:
        assert self.resolver.config is self.config


class TestEndpointResolverBareSuffix:
    """Auth-style endpoints with empty suffix."""

    def setup_method(self) -> None:
        config = EndpointConfig(
            base="auth/user",
            payload_key="user",
            entity_suffix="",
            apply_endpoint=None,
        )
        self.resolver = EndpointResolver(config)

    def test_search(self) -> None:
        assert self.resolver.search() == "auth/user/search"

    def test_get(self) -> None:
        assert self.resolver.get("uuid") == "auth/user/get/uuid"

    def test_add(self) -> None:
        assert self.resolver.add() == "auth/user/add"

    def test_set(self) -> None:
        assert self.resolver.set() == "auth/user/set"

    def test_delete(self) -> None:
        assert self.resolver.delete() == "auth/user/del"
