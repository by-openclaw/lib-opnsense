"""Unit tests for opnsense.managers.if_vip.IfVipManager.

Tests cover all BaseManager endpoints:
    - ensure(present): create, noop, update
    - ensure(absent): delete, noop
    - check_mode: create, delete, noop
    - list(), get(uuid), get_schema()
    - reconfigure after mutations
    - redact: password field (CARP)
    - error handling: create/delete failure, invalid state, type preserved
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
from opnsense.managers.if_vip import IfVipManager

# Standard test params — IP alias on LAN (SVC VLAN)
VIP_PARAMS = {
    "interface": "lan",
    "mode": "ipalias",
    "address": "10.1.3.200",
    "network": "32",
    "descr": "inttest-vip-svc",
}


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_vip(self, mock_client: AsyncMock) -> None:
        """ensure present when VIP does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(state="present", params=VIP_PARAMS)

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once_with(
            "interfaces/vip_settings/addItem", "vip", VIP_PARAMS
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "interfaces/vip_settings/reconfigure", timeout=None
        )

    async def test_noop_when_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when VIP exists with matching params -> noop."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **VIP_PARAMS}]

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(state="present", params=VIP_PARAMS)

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-1"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_network_changes(self, mock_client: AsyncMock) -> None:
        """ensure present when network changed -> update + reconfigure."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **VIP_PARAMS}]
        mock_client.get.return_value = {"vip": {"uuid": "uuid-1", **VIP_PARAMS}}
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        updated = {**VIP_PARAMS, "network": "24"}
        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(state="present", params=updated)

        assert result.changed is True
        assert result.action == "updated"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once()


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_vip(self, mock_client: AsyncMock) -> None:
        """ensure absent when VIP exists -> delete + reconfigure."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **VIP_PARAMS}]
        mock_client.get.return_value = {"vip": {"uuid": "uuid-1", **VIP_PARAMS}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"address": "10.1.3.200", "interface": "lan", "mode": "ipalias"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when VIP does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(state="absent", params={"descr": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(state="present", params=VIP_PARAMS, check_mode=True)

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **VIP_PARAMS}]
        mock_client.get.return_value = {"vip": {"uuid": "uuid-1", **VIP_PARAMS}}

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"address": "10.1.3.200", "interface": "lan", "mode": "ipalias"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()

    async def test_check_mode_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **VIP_PARAMS}]

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(state="present", params=VIP_PARAMS, check_mode=True)

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestEndpoints:
    """Tests for correct endpoint URL construction."""

    async def test_list_uses_search_item(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = IfVipManager(mock_client)
        await mgr.list()
        mock_client.search.assert_awaited_once_with(
            "interfaces/vip_settings/searchItem", search_phrase=""
        )

    async def test_get_calls_get_item_with_uuid(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"vip": {"descr": "test"}}
        mgr = IfVipManager(mock_client)
        result = await mgr.get("uuid-1")
        mock_client.get.assert_awaited_once_with("interfaces/vip_settings/getItem/uuid-1")
        assert result == {"descr": "test"}

    async def test_get_schema(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"vip": {"mode": "ipalias", "address": ""}}
        mgr = IfVipManager(mock_client)
        result = await mgr.get_schema()
        mock_client.get.assert_awaited_once_with("interfaces/vip_settings/getItem")
        assert "mode" in result


@pytest.mark.asyncio
class TestRedactFields:
    """VIP redacts CARP password."""

    async def test_password_in_redact_fields(self) -> None:
        assert "password" in IfVipManager.REDACT_FIELDS

    async def test_create_redacts_password_in_result(self, mock_client: AsyncMock) -> None:
        """ensure present create -> password is redacted in after dict."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={**VIP_PARAMS, "mode": "carp", "password": "s3cret"},
        )

        assert result.after is not None
        assert result.after["password"] == "<REDACTED:password>"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="address required",
            endpoint="interfaces/vip_settings/addItem",
        )

        mgr = IfVipManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "descr": "bad",
                    "address": "10.1.3.200",
                    "interface": "lan",
                    "mode": "ipalias",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "address": "10.1.3.200", "interface": "lan", "mode": "ipalias"},
        ]
        mock_client.get.return_value = {
            "vip": {
                "uuid": "uuid-1",
                "address": "10.1.3.200",
                "interface": "lan",
                "mode": "ipalias",
            },
        }
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = IfVipManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(
                state="absent",
                params={"address": "10.1.3.200", "interface": "lan", "mode": "ipalias"},
            )

        assert any("delete failed" in r.message for r in caplog.records)

    async def test_invalid_state_raises_value_error(self, mock_client: AsyncMock) -> None:
        mgr = IfVipManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"descr": "test"})

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad",
            endpoint="interfaces/vip_settings/addItem",
            validations={"vip.address": "required"},
        )

        mgr = IfVipManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "descr": "bad",
                    "address": "10.1.3.200",
                    "interface": "lan",
                    "mode": "ipalias",
                },
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.validations == {"vip.address": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_invalid_mode_enum_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """mode='invalid' fails enum validation before API call."""
        mgr = IfVipManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "address": "10.1.3.200",
                    "interface": "lan",
                    "mode": "invalid",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_address_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'address' raises FieldValidationError."""
        mgr = IfVipManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"interface": "lan", "mode": "ipalias"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "aaa",
                "address": "10.1.3.200",
                "interface": "lan",
                "mode": "ipalias",
            },
            {
                "uuid": "bbb",
                "address": "10.1.3.200",
                "interface": "lan",
                "mode": "ipalias",
            },
        ]
        mgr = IfVipManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                params={
                    "address": "10.1.3.200",
                    "interface": "lan",
                    "mode": "ipalias",
                    "network": "32",
                },
            )
        assert exc_info.value.uuids == ["aaa", "bbb"]
        mock_client.create.assert_not_awaited()
