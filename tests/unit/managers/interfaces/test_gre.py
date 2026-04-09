"""Unit tests for opnsense.managers.if_gre.IfGreManager.

Tests cover all BaseManager endpoints:
    - ensure(present): create, noop (no drift), update (drift)
    - ensure(absent): delete, noop (already absent)
    - check_mode: create, delete, noop
    - reconfigure: applied after create/update/delete
    - error handling: create failure logs + re-raises, invalid state, type preserved
    - field validation: required tunnel-local-addr, tunnel-remote-addr
    - ambiguous match: multiple resources match composite keys
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseError,
    OpnsenseValidationError,
)
from opnsense.managers.interfaces.gre import IfGreManager

GRE_PARAMS = {
    "tunnel-local-addr": "10.0.0.1",
    "tunnel-remote-addr": "10.0.0.2",
    "descr": "GRE Tunnel",
}


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_gre(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(state="present", params=GRE_PARAMS)

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once_with(
            "interfaces/gre_settings/addItem", "gre", GRE_PARAMS
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "interfaces/gre_settings/reconfigure", timeout=None
        )

    async def test_noop_when_no_drift(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **GRE_PARAMS}]

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(state="present", params=GRE_PARAMS)

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-1"
        mock_client.create.assert_not_awaited()
        mock_client.update.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **GRE_PARAMS}]
        mock_client.get.return_value = {"gre": {"uuid": "uuid-1", **GRE_PARAMS}}
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "tunnel-local-addr": "10.0.0.1",
                "tunnel-remote-addr": "10.0.0.2",
                "descr": "GRE Tunnel Updated",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        assert result.uuid == "uuid-1"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "interfaces/gre_settings/reconfigure", timeout=None
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_gre(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **GRE_PARAMS}]
        mock_client.get.return_value = {"gre": {"uuid": "uuid-1", **GRE_PARAMS}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"tunnel-local-addr": "10.0.0.1", "tunnel-remote-addr": "10.0.0.2"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        assert result.uuid == "uuid-1"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(state="absent", params={"tunnel-local-addr": "10.0.0.99"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(state="present", params=GRE_PARAMS, check_mode=True)

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **GRE_PARAMS}]
        mock_client.get.return_value = {"gre": {"uuid": "uuid-1", **GRE_PARAMS}}

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"tunnel-local-addr": "10.0.0.1", "tunnel-remote-addr": "10.0.0.2"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_noop_stays_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **GRE_PARAMS}]

        mgr = IfGreManager(mock_client)
        result = await mgr.ensure(state="present", params=GRE_PARAMS, check_mode=True)

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid addr", endpoint="interfaces/gre_settings/addItem"
        )

        mgr = IfGreManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params=GRE_PARAMS)

        assert any("create failed" in r.message for r in caplog.records)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **GRE_PARAMS}]
        mock_client.get.return_value = {"gre": {"uuid": "uuid-1", **GRE_PARAMS}}
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = IfGreManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(
                state="absent",
                params={"tunnel-local-addr": "10.0.0.1", "tunnel-remote-addr": "10.0.0.2"},
            )

        assert any("delete failed" in r.message for r in caplog.records)

    async def test_invalid_state_raises_value_error(self, mock_client: AsyncMock) -> None:
        mgr = IfGreManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"tunnel-local-addr": "10.0.0.1"})

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="interfaces/gre_settings/addItem",
            validations={"gre.tunnel-local-addr": "required"},
        )

        mgr = IfGreManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params=GRE_PARAMS)

        assert exc_info.value.status_code == 400
        assert exc_info.value.validations == {"gre.tunnel-local-addr": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_tunnel_local_addr(self, mock_client: AsyncMock) -> None:
        mgr = IfGreManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"tunnel-remote-addr": "10.0.0.2"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_tunnel_remote_addr(self, mock_client: AsyncMock) -> None:
        mgr = IfGreManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"tunnel-local-addr": "10.0.0.1"})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "aaa",
                "tunnel-local-addr": "10.0.0.1",
                "tunnel-remote-addr": "10.0.0.2",
                "descr": "A",
            },
            {
                "uuid": "bbb",
                "tunnel-local-addr": "10.0.0.1",
                "tunnel-remote-addr": "10.0.0.2",
                "descr": "B",
            },
        ]
        mgr = IfGreManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure("present", params=GRE_PARAMS)
        assert exc_info.value.uuids == ["aaa", "bbb"]
        mock_client.create.assert_not_awaited()
