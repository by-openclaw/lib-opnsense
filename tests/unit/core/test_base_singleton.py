# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/base_singleton.py — BaseSingletonManager.

Covers the ADR ``lib/python/0001 §10.2`` mandatory test set, adapted for the
singleton pattern (no _match_keys → AmbiguousMatchError does not apply):

1. set / ensure failures log ERROR and re-raise unchanged
2. Exception type preserved through the manager layer
3. FieldValidationError raised BEFORE the API call for bad params
4. (N/A — no composite keys, no ambiguous match)
5. Consumer try/except/finally pattern works correctly
6. Transport errors propagate: 401, 403, 404, 400, 500, timeout, connection
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest

from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.exceptions import (
    FieldValidationError,
    OpnsenseAuthError,
    OpnsenseConnectionError,
    OpnsenseEndpointMissingError,
    OpnsensePermissionError,
    OpnsenseServerError,
    OpnsenseTimeoutError,
    OpnsenseValidationError,
)


class _DummySingleton(BaseSingletonManager):
    """Concrete subclass for testing the singleton base pattern."""

    _endpoint = "dummy/settings"
    _payload_key = "dummy"
    _apply_endpoint = "dummy/service/reconfigure"
    _validators = {
        "enable": {"type": "bool_str", "required": True},
        "port": {"type": "int", "min": 1, "max": 65535},
    }


class _NoApplySingleton(BaseSingletonManager):
    """Singleton whose daemon applies changes immediately (no reconfigure)."""

    _endpoint = "auth/settings"
    _payload_key = "auth"
    _apply_endpoint = None


@pytest.mark.asyncio
class TestGet:
    """Tests for ``get()``."""

    async def test_returns_inner_payload(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dummy": {"enable": "1", "port": "53"}}
        mgr = _DummySingleton(mock_client)
        result = await mgr.get()
        assert result == {"enable": "1", "port": "53"}
        mock_client.get.assert_awaited_once_with("dummy/settings/get")

    async def test_returns_body_when_payload_key_missing(self, mock_client: AsyncMock) -> None:
        """When the API returns no payload_key wrapper, fall back to the body itself."""
        mock_client.get.return_value = {"enable": "1"}
        mgr = _DummySingleton(mock_client)
        result = await mgr.get()
        assert result == {"enable": "1"}

    async def test_logs_error_and_reraises_on_failure(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.get.side_effect = OpnsenseServerError("boom")
        mgr = _DummySingleton(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.core.base_singleton"),
            pytest.raises(OpnsenseServerError),
        ):
            await mgr.get()
        assert any("get failed dummy/settings" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestSet:
    """Tests for ``set()``."""

    async def test_noop_when_state_matches(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dummy": {"enable": "1", "port": "53"}}
        mgr = _DummySingleton(mock_client)
        result = await mgr.set({"enable": "1"})
        assert result.changed is False
        assert result.action == "noop"
        # No write call
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_updates_when_drifted(self, mock_client: AsyncMock) -> None:
        # First get returns drifted state, second get (after set) returns desired
        mock_client.get.side_effect = [
            {"dummy": {"enable": "0", "port": "53"}},
            {"dummy": {"enable": "1", "port": "53"}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = _DummySingleton(mock_client)
        result = await mgr.set({"enable": "1"})

        assert result.changed is True
        assert result.action == "updated"
        assert result.before == {"enable": "0", "port": "53"}
        assert result.after == {"enable": "1", "port": "53"}
        mock_client.post.assert_awaited_once_with(
            "dummy/settings/set",
            {"dummy": {"enable": "1"}},
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "dummy/service/reconfigure",
            timeout=None,
        )

    async def test_check_mode_returns_projected_after_without_calling_api(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = {"dummy": {"enable": "0", "port": "53"}}

        mgr = _DummySingleton(mock_client)
        result = await mgr.set({"enable": "1"}, check_mode=True)

        assert result.changed is True
        assert result.action == "updated"
        assert result.after == {"enable": "1", "port": "53"}
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_skips_reconfigure_when_apply_endpoint_is_none(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get.side_effect = [
            {"auth": {"enable": "0"}},
            {"auth": {"enable": "1"}},
        ]
        mock_client.post.return_value = {"result": "saved"}

        mgr = _NoApplySingleton(mock_client)
        result = await mgr.set({"enable": "1"})

        assert result.changed is True
        mock_client.reconfigure.assert_not_awaited()

    async def test_logs_error_and_reraises_when_post_fails(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.get.return_value = {"dummy": {"enable": "0"}}
        mock_client.post.side_effect = OpnsenseValidationError("bad value")

        mgr = _DummySingleton(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.core.base_singleton"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.set({"enable": "x"})
        assert any("set failed dummy/settings" in r.message for r in caplog.records)

    async def test_apply_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dummy": {"enable": "0"}}
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.side_effect = OpnsenseTimeoutError("reconfigure timeout")

        mgr = _DummySingleton(mock_client)
        with pytest.raises(OpnsenseTimeoutError):
            await mgr.set({"enable": "1"})


@pytest.mark.asyncio
class TestEnsure:
    """Tests for ``ensure()``."""

    async def test_rejects_state_absent(self, mock_client: AsyncMock) -> None:
        mgr = _DummySingleton(mock_client)
        with pytest.raises(ValueError, match="state='present'"):
            await mgr.ensure("absent", {"enable": "1"})

    async def test_rejects_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = _DummySingleton(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("running", {"enable": "1"})

    async def test_field_validation_runs_before_api_call(self, mock_client: AsyncMock) -> None:
        """Bad params must raise FieldValidationError without touching the API."""
        mgr = _DummySingleton(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"enable": "not-a-bool", "port": "53"})

        mock_client.get.assert_not_awaited()
        mock_client.post.assert_not_awaited()

    async def test_missing_required_field_raises(self, mock_client: AsyncMock) -> None:
        mgr = _DummySingleton(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"port": "53"})  # missing 'enable'

        mock_client.get.assert_not_awaited()

    async def test_ensure_noop_path(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"dummy": {"enable": "1", "port": "53"}}

        mgr = _DummySingleton(mock_client)
        result = await mgr.ensure("present", {"enable": "1"})

        assert result.changed is False
        assert result.action == "noop"

    async def test_ensure_update_path(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"dummy": {"enable": "0", "port": "53"}},
            {"dummy": {"enable": "1", "port": "53"}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = _DummySingleton(mock_client)
        result = await mgr.ensure("present", {"enable": "1"})

        assert result.changed is True
        assert result.action == "updated"


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
    async def test_get_propagates_typed_transport_errors(
        self,
        mock_client: AsyncMock,
        exc_type: type[Exception],
    ) -> None:
        mock_client.get.side_effect = exc_type("transport error")
        mgr = _DummySingleton(mock_client)
        with pytest.raises(exc_type):
            await mgr.get()


@pytest.mark.asyncio
class TestConsumerPattern:
    """Per ADR §10.2 case 5 — consumer try/except/finally must work as documented."""

    async def test_consumer_can_catch_typed_exceptions(self, mock_client: AsyncMock) -> None:
        """Verify the documented consumer contract holds end-to-end."""
        mock_client.get.return_value = {"dummy": {"enable": "0"}}
        mock_client.post.side_effect = OpnsenseValidationError("server rejected")

        mgr = _DummySingleton(mock_client)
        caught: dict[str, Any] = {"validation": False, "finally": False}
        try:
            await mgr.ensure("present", {"enable": "1"})
        except OpnsenseValidationError:
            caught["validation"] = True
        finally:
            caught["finally"] = True

        assert caught == {"validation": True, "finally": True}
