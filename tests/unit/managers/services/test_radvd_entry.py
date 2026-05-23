# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.radvd_entry.RadvdEntryManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
    OpnsenseValidationError,
)
from opnsense.managers.services.radvd_entry import RadvdEntryManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """ensure(state='present') — create / update / noop."""

    async def test_creates_when_missing(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RadvdEntryManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"interface": "opt2", "mode": "managed", "enabled": "1"},
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("radvd/service/reconfigure", timeout=30)

    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "interface": "opt2",
                "enabled": "1",
                "mode": "managed",
            }
        ]

        mgr = RadvdEntryManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"interface": "opt2", "enabled": "1", "mode": "managed"},
        )

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-exists"
        mock_client.create.assert_not_awaited()
        mock_client.update.assert_not_awaited()

    async def test_updates_when_drifted(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "interface": "opt2",
                "enabled": "1",
                "mode": "stateless",
            }
        ]
        # update() pre-fetches via get()
        mock_client.get.return_value = {
            "entries": {"interface": "opt2", "enabled": "1", "mode": "stateless"}
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RadvdEntryManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"interface": "opt2", "enabled": "1", "mode": "managed"},
        )

        assert result.changed is True
        assert result.action == "updated"
        assert result.uuid == "uuid-exists"

    async def test_check_mode_does_not_call_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = RadvdEntryManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"interface": "opt5", "mode": "stateless"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    """ensure(state='absent') — delete / noop."""

    async def test_deletes_when_exists(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-gone", "interface": "opt2", "enabled": "0"}
        ]
        mock_client.get.return_value = {"entries": {"interface": "opt2", "enabled": "0"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RadvdEntryManager(mock_client)
        result = await mgr.ensure("absent", {"interface": "opt2"})

        assert result.changed is True
        assert result.action == "deleted"
        assert result.uuid == "uuid-gone"

    async def test_noop_when_already_gone(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = RadvdEntryManager(mock_client)
        result = await mgr.ensure("absent", {"interface": "opt2"})
        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestValidation:
    """ADR §10.2 case 3 — FieldValidationError raised BEFORE the API call."""

    async def test_missing_required_interface(self, mock_client: AsyncMock) -> None:
        mgr = RadvdEntryManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"mode": "managed"})
        mock_client.search.assert_not_awaited()

    async def test_invalid_mode_enum(self, mock_client: AsyncMock) -> None:
        mgr = RadvdEntryManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"interface": "opt2", "mode": "invalid-mode"})
        mock_client.search.assert_not_awaited()

    async def test_invalid_enabled_bool(self, mock_client: AsyncMock) -> None:
        mgr = RadvdEntryManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"interface": "opt2", "enabled": "not-a-bool"})
        mock_client.search.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """ADR §10.2 case 4 — AmbiguousMatchError on duplicate match keys."""

    async def test_raises_when_multiple_entries_match(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "interface": "opt2", "enabled": "1"},
            {"uuid": "uuid-2", "interface": "opt2", "enabled": "0"},
        ]
        mgr = RadvdEntryManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure("present", {"interface": "opt2", "mode": "managed"})
        assert set(exc_info.value.uuids) == {"uuid-1", "uuid-2"}


@pytest.mark.asyncio
class TestErrorPropagation:
    """ADR §10.2 cases 1+2+6 — failures logged, re-raised by type."""

    async def test_create_failure_logs_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("server down")
        mgr = RadvdEntryManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseServerError),
        ):
            await mgr.ensure("present", {"interface": "opt2", "mode": "managed"})

    async def test_server_side_validation_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError("server rejected")
        mgr = RadvdEntryManager(mock_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure("present", {"interface": "opt2", "mode": "managed"})
