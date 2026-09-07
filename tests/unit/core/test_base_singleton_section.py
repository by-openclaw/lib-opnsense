# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for ``BaseSingletonManager._section`` (nested settings block).

Some OPNsense settings documents nest the daemon config under a sub-key
(``{"monit": {"general": {...}}}``, ``{"unbound": {"general": {...},
"advanced": {...}}}``). With ``_section`` set the base unwraps that block on
``get`` and re-nests it on ``set``; with ``_section=None`` behaviour is
unchanged (covered by ``test_base_singleton.py``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.core.base_singleton import BaseSingletonManager


class _SectionSingleton(BaseSingletonManager):
    """Singleton owning only the ``general`` block of a nested document."""

    _endpoint = "nested/settings"
    _payload_key = "nested"
    _section = "general"
    _apply_endpoint = "nested/service/reconfigure"
    _apply_timeout = 15


@pytest.mark.asyncio
class TestSectionGet:
    async def test_get_unwraps_section(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "nested": {"general": {"enabled": "0"}, "advanced": {"x": "1"}}
        }
        mgr = _SectionSingleton(mock_client)
        assert await mgr.get() == {"enabled": "0"}

    async def test_get_returns_empty_when_section_missing(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"nested": {"advanced": {"x": "1"}}}
        mgr = _SectionSingleton(mock_client)
        assert await mgr.get() == {}

    async def test_get_returns_empty_when_section_not_a_dict(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"nested": {"general": "garbage"}}
        mgr = _SectionSingleton(mock_client)
        assert await mgr.get() == {}


@pytest.mark.asyncio
class TestSectionSet:
    async def test_set_nests_params_under_section(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"nested": {"general": {"enabled": "0"}}},
            {"nested": {"general": {"enabled": "1"}}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = _SectionSingleton(mock_client)
        result = await mgr.set({"enabled": "1"})
        assert result.changed is True
        assert result.before == {"enabled": "0"}
        assert result.after == {"enabled": "1"}
        mock_client.post.assert_awaited_once_with(
            "nested/settings/set",
            {"nested": {"general": {"enabled": "1"}}},
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "nested/service/reconfigure",
            timeout=15,
        )

    async def test_noop_diffs_only_the_section(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "nested": {"general": {"enabled": "1"}, "advanced": {"enabled": "0"}}
        }
        mgr = _SectionSingleton(mock_client)
        result = await mgr.set({"enabled": "1"})
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()
