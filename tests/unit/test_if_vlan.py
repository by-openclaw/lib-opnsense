"""Unit tests for opnsense.managers.if_vlan.IfVlanManager.

Tests cover all BaseManager endpoints:
    - ensure(present): create, noop (no drift), update (drift)
    - ensure(absent): delete, noop (already absent)
    - check_mode: create, delete, noop
    - list(): search_item endpoint
    - get(uuid): get_item/{uuid} endpoint
    - get_schema(): get_item endpoint (no uuid)
    - reconfigure: applied after create/update/delete
    - error handling: create failure logs + re-raises, invalid state, type preserved
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
from opnsense.managers.if_vlan import IfVlanManager

# Standard test params matching real OPNsense VLAN config
VLAN_PARAMS = {"descr": "SVC", "if": "vtnet1", "tag": "330"}


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_vlan(self, mock_client: AsyncMock) -> None:
        """ensure present when VLAN does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(state="present", params=VLAN_PARAMS)

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once_with(
            "interfaces/vlan_settings/addItem", "vlan", VLAN_PARAMS
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "interfaces/vlan_settings/reconfigure", timeout=None
        )

    async def test_noop_when_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when VLAN exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", **VLAN_PARAMS},
        ]

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(state="present", params=VLAN_PARAMS)

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-1"
        mock_client.create.assert_not_awaited()
        mock_client.update.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when descr changed -> update + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "descr": "SVC", "if": "vtnet1", "tag": "330"},
        ]
        mock_client.get.return_value = {
            "vlan": {"uuid": "uuid-1", "descr": "SVC", "if": "vtnet1", "tag": "330"},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"descr": "SVC-updated", "if": "vtnet1", "tag": "330"},
        )

        assert result.changed is True
        assert result.action == "updated"
        assert result.uuid == "uuid-1"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "interfaces/vlan_settings/reconfigure", timeout=None
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_vlan(self, mock_client: AsyncMock) -> None:
        """ensure absent when VLAN exists -> delete + reconfigure."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **VLAN_PARAMS}]
        mock_client.get.return_value = {"vlan": {"uuid": "uuid-1", **VLAN_PARAMS}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(state="absent", params={"tag": "330", "if": "vtnet1"})

        assert result.changed is True
        assert result.action == "deleted"
        assert result.uuid == "uuid-1"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when VLAN does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(state="absent", params={"descr": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no create/reconfigure API call."""
        mock_client.search.return_value = []

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(state="present", params=VLAN_PARAMS, check_mode=True)

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode delete -> changed=True but no delete API call."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **VLAN_PARAMS}]
        mock_client.get.return_value = {"vlan": {"uuid": "uuid-1", **VLAN_PARAMS}}

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(
            state="absent", params={"tag": "330", "if": "vtnet1"}, check_mode=True
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_noop_stays_noop(self, mock_client: AsyncMock) -> None:
        """check_mode on already matching state -> noop."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **VLAN_PARAMS}]

        mgr = IfVlanManager(mock_client)
        result = await mgr.ensure(state="present", params=VLAN_PARAMS, check_mode=True)

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestEndpoints:
    """Tests for correct endpoint URL construction."""

    async def test_list_uses_search_item(self, mock_client: AsyncMock) -> None:
        """list() calls searchItem endpoint."""
        mock_client.search.return_value = []
        mgr = IfVlanManager(mock_client)
        await mgr.list()
        mock_client.search.assert_awaited_once_with(
            "interfaces/vlan_settings/searchItem", search_phrase=""
        )

    async def test_get_calls_get_item_with_uuid(self, mock_client: AsyncMock) -> None:
        """get(uuid) calls getItem/{uuid} endpoint."""
        mock_client.get.return_value = {"vlan": {"descr": "SVC"}}
        mgr = IfVlanManager(mock_client)
        result = await mgr.get("uuid-1")
        mock_client.get.assert_awaited_once_with("interfaces/vlan_settings/getItem/uuid-1")
        assert result == {"descr": "SVC"}

    async def test_get_schema_calls_get_item_no_uuid(self, mock_client: AsyncMock) -> None:
        """get_schema() calls getItem without UUID."""
        mock_client.get.return_value = {"vlan": {"descr": "", "tag": ""}}
        mgr = IfVlanManager(mock_client)
        result = await mgr.get_schema()
        mock_client.get.assert_awaited_once_with("interfaces/vlan_settings/getItem")
        assert "descr" in result


@pytest.mark.asyncio
class TestRedactFields:
    """VLAN has no sensitive fields."""

    async def test_no_redact_fields(self) -> None:
        assert len(IfVlanManager.REDACT_FIELDS) == 0


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When create() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="tag required", endpoint="interfaces/vlan_settings/addItem"
        )

        mgr = IfVlanManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"descr": "bad", "tag": "330", "if": "vtnet1"})

        assert any("create failed" in r.message for r in caplog.records)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When delete() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "tag": "330", "if": "vtnet1", "descr": "SVC"},
        ]
        mock_client.get.return_value = {
            "vlan": {"uuid": "uuid-1", "tag": "330", "if": "vtnet1", "descr": "SVC"},
        }
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = IfVlanManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(state="absent", params={"tag": "330", "if": "vtnet1"})

        assert any("delete failed" in r.message for r in caplog.records)

    async def test_invalid_state_raises_value_error(self, mock_client: AsyncMock) -> None:
        """Invalid state raises ValueError immediately."""
        mgr = IfVlanManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"descr": "SVC"})

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        """Re-raised exception keeps its original type (not wrapped)."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="interfaces/vlan_settings/addItem",
            validations={"vlan.tag": "required"},
        )

        mgr = IfVlanManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params={"descr": "bad", "tag": "330", "if": "vtnet1"})

        assert exc_info.value.status_code == 400
        assert exc_info.value.validations == {"vlan.tag": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_tag_out_of_range_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """tag=99999 exceeds max 4094, raises FieldValidationError before API call."""
        mgr = IfVlanManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"tag": "99999", "if": "vtnet1"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_tag_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'tag' raises FieldValidationError."""
        mgr = IfVlanManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"if": "vtnet1", "descr": "Test"})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "aaa", "tag": "330", "if": "vtnet1", "descr": "SVC-1"},
            {"uuid": "bbb", "tag": "330", "if": "vtnet1", "descr": "SVC-2"},
        ]
        mgr = IfVlanManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                params={"tag": "330", "if": "vtnet1", "descr": "SVC-1"},
            )
        assert exc_info.value.uuids == ["aaa", "bbb"]
        mock_client.create.assert_not_awaited()
