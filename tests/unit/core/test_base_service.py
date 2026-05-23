# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/base_service.py — BaseServiceManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set adapted for the
service controller pattern (no CRUD, no _match_keys → some cases N/A):

1. Action failures (start/stop/restart/reconfigure) log ERROR and re-raise
2. Exception type preserved through the manager layer
3. (N/A — no _validators in service base; ValueError tested instead)
4. (N/A — no composite keys)
5. Consumer try/except/finally pattern works correctly
6. Transport errors propagate: 401, 403, 404, 400, 500, timeout, connection
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest

from opnsense.core.base_service import BaseServiceManager
from opnsense.exceptions import (
    OpnsenseAuthError,
    OpnsenseConnectionError,
    OpnsenseEndpointMissingError,
    OpnsensePermissionError,
    OpnsenseServerError,
    OpnsenseTimeoutError,
    OpnsenseValidationError,
)


class _DummyService(BaseServiceManager):
    """Concrete subclass for testing the service base pattern."""

    _endpoint = "dummy/service"


class _SlowService(BaseServiceManager):
    """Concrete subclass with apply_timeout override."""

    _endpoint = "slow/service"
    _apply_timeout = 120


@pytest.mark.asyncio
class TestStatus:
    """Tests for ``status()``."""

    async def test_returns_status_field(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running", "widget": {}}
        mgr = _DummyService(mock_client)
        result = await mgr.status()
        assert result == "running"
        mock_client.get.assert_awaited_once_with("dummy/service/status")

    async def test_unknown_when_status_field_missing(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"widget": {}}
        mgr = _DummyService(mock_client)
        result = await mgr.status()
        assert result == "unknown"

    async def test_logs_error_and_reraises_on_failure(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.get.side_effect = OpnsenseServerError("boom")
        mgr = _DummyService(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.core.base_service"),
            pytest.raises(OpnsenseServerError),
        ):
            await mgr.status()
        assert any("status failed dummy/service" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestEnsureRunning:
    """ensure(state='running') — idempotent start."""

    async def test_noop_when_already_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mgr = _DummyService(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_starts_when_stopped(self, mock_client: AsyncMock) -> None:
        # status() called twice: ensure() pre-check + _action() pre-check + post-check
        mock_client.get.side_effect = [
            {"status": "stopped"},  # ensure() pre-check
            {"status": "stopped"},  # _action() pre-check
            {"status": "running"},  # _action() post-check
        ]
        mock_client.post.return_value = {"response": "OK"}

        mgr = _DummyService(mock_client)
        result = await mgr.ensure("running")

        assert result.changed is True
        assert result.action == "started"
        assert result.before == {"status": "stopped"}
        assert result.after == {"status": "running"}
        mock_client.post.assert_awaited_once_with(
            "dummy/service/start",
            {},
            timeout=None,
        )

    async def test_check_mode_does_not_call_post(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "stopped"},  # ensure() pre-check
            {"status": "stopped"},  # _action() pre-check
        ]
        mgr = _DummyService(mock_client)
        result = await mgr.ensure("running", check_mode=True)
        assert result.changed is True
        assert result.action == "started"
        mock_client.post.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureStopped:
    """ensure(state='stopped') — idempotent stop."""

    @pytest.mark.parametrize("already", ["stopped", "disabled", "unknown"])
    async def test_noop_when_not_running(self, mock_client: AsyncMock, already: str) -> None:
        mock_client.get.return_value = {"status": already}
        mgr = _DummyService(mock_client)
        result = await mgr.ensure("stopped")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_stops_when_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "running"},
            {"status": "running"},
            {"status": "stopped"},
        ]
        mock_client.post.return_value = {"response": "OK"}

        mgr = _DummyService(mock_client)
        result = await mgr.ensure("stopped")

        assert result.changed is True
        assert result.action == "stopped"


@pytest.mark.asyncio
class TestEnsureReconfigured:
    """ensure(state='reconfigured') — no idempotency, always acts."""

    async def test_always_calls_reconfigure_regardless_of_status(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get.side_effect = [
            {"status": "running"},  # _action pre-check (ensure delegates straight in)
            {"status": "running"},  # _action post-check
        ]
        mock_client.post.return_value = {"status": "ok"}

        mgr = _DummyService(mock_client)
        result = await mgr.ensure("reconfigured")

        assert result.changed is True
        assert result.action == "reconfigured"
        mock_client.post.assert_awaited_once_with(
            "dummy/service/reconfigure",
            {},
            timeout=None,
        )

    async def test_apply_timeout_is_passed_through(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"status": "running"},
            {"status": "running"},
        ]
        mock_client.post.return_value = {"status": "ok"}

        mgr = _SlowService(mock_client)
        await mgr.ensure("reconfigured")

        mock_client.post.assert_awaited_once_with(
            "slow/service/reconfigure",
            {},
            timeout=120,
        )


@pytest.mark.asyncio
class TestInvalidState:
    """ensure() rejects unsupported state values."""

    @pytest.mark.parametrize(
        "bad_state",
        ["", "present", "absent", "RUNNING", "restart", None],
    )
    async def test_raises_value_error(self, mock_client: AsyncMock, bad_state: Any) -> None:
        mgr = _DummyService(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure(bad_state)
        mock_client.get.assert_not_awaited()


@pytest.mark.asyncio
class TestActionFailures:
    """Per ADR §10.2 case 1+2 — action failures log ERROR and re-raise unchanged."""

    async def test_start_failure_logs_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.get.return_value = {"status": "stopped"}
        mock_client.post.side_effect = OpnsenseServerError("start crashed")

        mgr = _DummyService(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.core.base_service"),
            pytest.raises(OpnsenseServerError),
        ):
            await mgr.ensure("running")

        assert any("start failed dummy/service" in r.message for r in caplog.records)

    async def test_reconfigure_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mock_client.post.side_effect = OpnsenseTimeoutError("daemon hung")

        mgr = _DummyService(mock_client)
        with pytest.raises(OpnsenseTimeoutError):
            await mgr.ensure("reconfigured")


@pytest.mark.asyncio
class TestTransportErrorPropagation:
    """Per ADR §10.2 case 6 — every transport error type must propagate cleanly."""

    @pytest.mark.parametrize(
        "exc_type",
        [
            OpnsenseAuthError,
            OpnsensePermissionError,
            OpnsenseEndpointMissingError,
            OpnsenseValidationError,
            OpnsenseServerError,
            OpnsenseTimeoutError,
            OpnsenseConnectionError,
        ],
    )
    async def test_status_propagates_typed_transport_errors(
        self,
        mock_client: AsyncMock,
        exc_type: type[Exception],
    ) -> None:
        mock_client.get.side_effect = exc_type("transport error")
        mgr = _DummyService(mock_client)
        with pytest.raises(exc_type):
            await mgr.status()


@pytest.mark.asyncio
class TestConsumerPattern:
    """Per ADR §10.2 case 5 — consumer try/except/finally must work as documented."""

    async def test_consumer_can_catch_typed_exceptions(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "stopped"}
        mock_client.post.side_effect = OpnsenseAuthError("token expired")

        mgr = _DummyService(mock_client)
        caught: dict[str, Any] = {"auth": False, "finally": False}
        try:
            await mgr.ensure("running")
        except OpnsenseAuthError:
            caught["auth"] = True
        finally:
            caught["finally"] = True

        assert caught == {"auth": True, "finally": True}
