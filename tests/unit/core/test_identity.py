# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/identity.py — IdentityResolver."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.core.identity import IdentityResolver
from opnsense.exceptions import AmbiguousMatchError


class TestMatchLabel:
    """match_label produces 'key1=val1 key2=val2'."""

    def test_single_key(self) -> None:
        resolver = IdentityResolver(match_keys=["name"], endpoint="auth/user")
        assert resolver.match_label({"name": "rune"}) == "name=rune"

    def test_composite_keys(self) -> None:
        resolver = IdentityResolver(match_keys=["tag", "if"])
        assert resolver.match_label({"tag": "100", "if": "lan"}) == "tag=100 if=lan"

    def test_missing_key_shows_empty(self) -> None:
        resolver = IdentityResolver(match_keys=["name", "scope"])
        assert resolver.match_label({"name": "rune"}) == "name=rune scope="


class TestMatchLogFields:
    """match_log_fields returns structured log fields."""

    def test_returns_match_keys_and_endpoint(self) -> None:
        resolver = IdentityResolver(
            match_keys=["name"], endpoint="auth/user", manager_name="AuthUserManager"
        )
        fields = resolver.match_log_fields({"name": "rune"})
        assert fields == {
            "match_keys": {"name": "rune"},
            "endpoint": "auth/user",
        }

    def test_composite_keys(self) -> None:
        resolver = IdentityResolver(match_keys=["tag", "if"], endpoint="if/vlan")
        fields = resolver.match_log_fields({"tag": "100", "if": "lan"})
        assert fields["match_keys"] == {"tag": "100", "if": "lan"}


class TestFindExisting:
    """find_existing searches by composite match keys."""

    @pytest.mark.asyncio
    async def test_zero_matches_returns_none(self) -> None:
        resolver = IdentityResolver(match_keys=["name"])
        list_fn = AsyncMock(return_value=[])
        result = await resolver.find_existing({"name": "rune"}, list_fn)
        assert result is None

    @pytest.mark.asyncio
    async def test_single_match_returns_row(self) -> None:
        resolver = IdentityResolver(match_keys=["name"])
        row = {"uuid": "abc-123", "name": "rune", "email": "rune@example.com"}
        list_fn = AsyncMock(return_value=[row])
        result = await resolver.find_existing({"name": "rune"}, list_fn)
        assert result == row

    @pytest.mark.asyncio
    async def test_composite_keys_exact_match(self) -> None:
        resolver = IdentityResolver(match_keys=["tag", "if"])
        rows = [
            {"uuid": "1", "tag": "100", "if": "lan"},
            {"uuid": "2", "tag": "100", "if": "wan"},
        ]
        list_fn = AsyncMock(return_value=rows)
        result = await resolver.find_existing({"tag": "100", "if": "lan"}, list_fn)
        assert result is not None
        assert result["uuid"] == "1"

    @pytest.mark.asyncio
    async def test_multiple_matches_raises_ambiguous(self) -> None:
        resolver = IdentityResolver(
            match_keys=["name"], endpoint="auth/user", manager_name="AuthUserManager"
        )
        rows = [
            {"uuid": "aaa", "name": "rune"},
            {"uuid": "bbb", "name": "rune"},
        ]
        list_fn = AsyncMock(return_value=rows)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await resolver.find_existing({"name": "rune"}, list_fn)
        assert exc_info.value.uuids == ["aaa", "bbb"]
        assert exc_info.value.match_keys == {"name": "rune"}
        assert exc_info.value.endpoint == "auth/user"

    @pytest.mark.asyncio
    async def test_empty_primary_uses_next_nonempty_key_as_phrase(self) -> None:
        """Catch-all Unbound forward: domain='' is a legitimate identity."""
        resolver = IdentityResolver(match_keys=["domain", "server"])
        rows = [
            {"uuid": "1", "domain": "", "server": "127.0.0.1"},
            {"uuid": "2", "domain": "lab.test", "server": "127.0.0.1"},
        ]
        list_fn = AsyncMock(return_value=rows)
        result = await resolver.find_existing({"domain": "", "server": "127.0.0.1"}, list_fn)
        assert result is not None
        assert result["uuid"] == "1"
        list_fn.assert_called_once_with("127.0.0.1")

    @pytest.mark.asyncio
    async def test_all_keys_empty_lists_all_and_matches_exactly(self) -> None:
        resolver = IdentityResolver(match_keys=["name"])
        rows = [{"uuid": "1", "name": ""}, {"uuid": "2", "name": "x"}]
        list_fn = AsyncMock(return_value=rows)
        result = await resolver.find_existing({"name": ""}, list_fn)
        assert result is not None
        assert result["uuid"] == "1"
        list_fn.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_empty_primary_no_match_returns_none(self) -> None:
        resolver = IdentityResolver(match_keys=["domain", "server"])
        list_fn = AsyncMock(return_value=[{"uuid": "2", "domain": "lab.test", "server": "::1"}])
        result = await resolver.find_existing({"domain": "", "server": "::1"}, list_fn)
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_first_key_as_search_phrase(self) -> None:
        resolver = IdentityResolver(match_keys=["tag", "if"])
        list_fn = AsyncMock(return_value=[])
        await resolver.find_existing({"tag": "100", "if": "lan"}, list_fn)
        list_fn.assert_called_once_with("100")


class TestConstructorValidation:
    """Constructor rejects bad input."""

    def test_empty_match_keys_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            IdentityResolver(match_keys=[])

    def test_match_keys_property_returns_copy(self) -> None:
        resolver = IdentityResolver(match_keys=["a", "b"])
        keys = resolver.match_keys
        keys.append("c")
        assert resolver.match_keys == ["a", "b"]
