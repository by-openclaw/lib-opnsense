# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.ub_host_alias.UbHostAliasManager.

LIMITATION: OPNsense 26.1.5 does not expose setHostAlias or delHostAlias
endpoints (404). Tests focus on create + read paths. Update/delete tests
are omitted — they would fail with OpnsenseEndpointMissingError on real HW.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError, FieldValidationError, OpnsenseValidationError
from opnsense.managers.dns.ub_host_alias import UbHostAliasManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_alias(self, mock_client: AsyncMock) -> None:
        """ensure present when alias does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbHostAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "hostname": "web-alias",
                "domain": "lab.test",
                "host": "parent-uuid",
                "description": "inttest-alias",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when alias matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "hostname": "web-alias",
                "domain": "lab.test",
                "host": "parent-uuid",
                "description": "inttest-alias",
            },
        ]

        mgr = UbHostAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "hostname": "web-alias",
                "domain": "lab.test",
                "host": "parent-uuid",
                "description": "inttest-alias",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = UbHostAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "hostname": "web-alias",
                "domain": "lab.test",
                "host": "parent-uuid",
            },
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_hostname_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = UbHostAliasManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"domain": "lab.test", "host": "parent-uuid"})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """Tests for AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        """Two aliases with same composite keys -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "hostname": "web-alias", "domain": "lab.test", "host": "p1"},
            {"uuid": "uuid-2", "hostname": "web-alias", "domain": "lab.test", "host": "p2"},
        ]

        mgr = UbHostAliasManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "hostname": "web-alias",
                    "domain": "lab.test",
                    "host": "parent-uuid",
                },
            )

        assert len(exc_info.value.uuids) == 2
        assert "uuid-1" in exc_info.value.uuids
        assert "uuid-2" in exc_info.value.uuids

    async def test_no_ambiguity_different_composite_key(self, mock_client: AsyncMock) -> None:
        """Two aliases with same hostname but different domain -> no ambiguity."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "hostname": "web-alias", "domain": "lab.test", "host": "p1"},
            {"uuid": "uuid-2", "hostname": "web-alias", "domain": "other.test", "host": "p2"},
        ]

        mgr = UbHostAliasManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "hostname": "web-alias",
                "domain": "lab.test",
                "host": "p1",
            },
        )
        assert result.action == "noop"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid alias", endpoint="unbound/settings/addHostAlias"
        )

        mgr = UbHostAliasManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "hostname": "bad",
                    "domain": "lab.test",
                    "host": "parent-uuid",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)
