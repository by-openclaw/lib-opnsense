"""Unit tests for opnsense.managers.fw_one_to_one.FwOneToOneManager."""

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
from opnsense.managers.fw_one_to_one import FwOneToOneManager

# Standard test params matching real OPNsense 1:1 NAT config
OTO_PARAMS = {
    "description": "1:1 NAT WAN to DMZ Traefik",
    "interface": "wan",
    "source_net": "10.1.2.10/32",
    "external": "10.6.224.106",
}


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(state="present", params=OTO_PARAMS)

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/one_to_one/apply", timeout=None)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when rule matches -> noop."""
        mock_client.search.return_value = [{"uuid": "uuid-existing", **OTO_PARAMS}]

        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(state="present", params=OTO_PARAMS)

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-existing"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when external differs -> update + apply."""
        mock_client.search.return_value = [{"uuid": "uuid-existing", **OTO_PARAMS}]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", **OTO_PARAMS},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        updated = {**OTO_PARAMS, "external": "10.6.224.107"}
        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(state="present", params=updated)

        assert result.changed is True
        assert result.action == "updated"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/one_to_one/apply", timeout=None)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_rule(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule exists -> delete + apply."""
        mock_client.search.return_value = [{"uuid": "uuid-existing", **OTO_PARAMS}]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", **OTO_PARAMS},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": OTO_PARAMS["description"],
                "interface": OTO_PARAMS["interface"],
                "source_net": OTO_PARAMS["source_net"],
            },
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/one_to_one/apply", timeout=None)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(state="present", params=OTO_PARAMS, check_mode=True)
        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **OTO_PARAMS}]
        mock_client.get.return_value = {"rule": {"uuid": "uuid-1", **OTO_PARAMS}}
        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": OTO_PARAMS["description"],
                "interface": OTO_PARAMS["interface"],
                "source_net": OTO_PARAMS["source_net"],
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_noop_stays_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", **OTO_PARAMS}]
        mgr = FwOneToOneManager(mock_client)
        result = await mgr.ensure(state="present", params=OTO_PARAMS, check_mode=True)
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally -- errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When create() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid rule", endpoint="firewall/one_to_one/addRule"
        )

        mgr = FwOneToOneManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params=OTO_PARAMS)

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When delete() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **OTO_PARAMS}]
        mock_client.get.return_value = {"rule": {"uuid": "uuid-1", **OTO_PARAMS}}
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = FwOneToOneManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(
                state="absent",
                params={
                    "description": OTO_PARAMS["description"],
                    "interface": OTO_PARAMS["interface"],
                    "source_net": OTO_PARAMS["source_net"],
                },
            )

        assert any("delete failed" in r.message for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        """Re-raised exception keeps its original type (not wrapped)."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="firewall/one_to_one/addRule",
            validations={"rule.interface": "required"},
        )

        mgr = FwOneToOneManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params=OTO_PARAMS)

        assert exc_info.value.status_code == 400
        assert exc_info.value.validations == {"rule.interface": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_empty_description_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """Empty required 'description' raises FieldValidationError."""
        mgr = FwOneToOneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "",
                    "interface": "wan",
                    "source_net": "10.1.2.10/32",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = FwOneToOneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"interface": "wan", "source_net": "10.1.2.10/32"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "aaa",
                "description": "1:1 NAT",
                "interface": "wan",
                "source_net": "10.1.2.10/32",
            },
            {
                "uuid": "bbb",
                "description": "1:1 NAT",
                "interface": "wan",
                "source_net": "10.1.2.10/32",
            },
        ]
        mgr = FwOneToOneManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                params={
                    "description": "1:1 NAT",
                    "interface": "wan",
                    "source_net": "10.1.2.10/32",
                },
            )
        assert exc_info.value.uuids == ["aaa", "bbb"]
        mock_client.create.assert_not_awaited()

    async def test_ambiguous_match_on_delete(self, mock_client: AsyncMock) -> None:
        """Delete with ambiguous match -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "aaa",
                "description": "dup",
                "interface": "wan",
                "source_net": "10.1.2.10/32",
            },
            {
                "uuid": "bbb",
                "description": "dup",
                "interface": "wan",
                "source_net": "10.1.2.10/32",
            },
        ]
        mgr = FwOneToOneManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                "absent",
                params={
                    "description": "dup",
                    "interface": "wan",
                    "source_net": "10.1.2.10/32",
                },
            )
