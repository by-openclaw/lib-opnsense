"""Unit tests for opnsense.managers.fw_filter.FwFilterManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError, FieldValidationError, OpnsenseValidationError
from opnsense.managers.fw_filter import FwFilterManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "interface": "lan",
                "protocol": "TCP",
                "destination_port": "443",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/filter/apply", timeout=None)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when rule matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "interface": "lan",
                "protocol": "TCP",
            },
        ]

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "interface": "lan",
                "protocol": "TCP",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when action differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Block SSH",
                "action": "pass",
                "interface": "lan",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "description": "Block SSH",
                "action": "pass",
                "interface": "lan",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Block SSH", "action": "block", "interface": "lan"},
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("firewall/filter/apply", timeout=None)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_rule(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "Block SSH"},
        ]
        mock_client.get.return_value = {
            "rule": {"uuid": "uuid-existing", "description": "Block SSH"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "Block SSH"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("firewall/filter/apply", timeout=None)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Test rule", "action": "pass", "interface": "lan"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Rule entity suffix."""

    async def test_search_uses_search_rule(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwFilterManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with("firewall/filter/searchRule", search_phrase="")

    async def test_create_uses_add_rule(self, mock_client: AsyncMock) -> None:
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwFilterManager(mock_client)
        await mgr.create(params={"description": "test", "action": "pass"})

        mock_client.create.assert_awaited_once_with(
            "firewall/filter/addRule", "rule", {"description": "test", "action": "pass"}
        )


@pytest.mark.asyncio
class TestRedactFields:
    """FwFilterManager has no sensitive fields."""

    async def test_no_redact_fields(self) -> None:
        assert len(FwFilterManager.REDACT_FIELDS) == 0


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid rule", endpoint="firewall/filter/addRule"
        )

        mgr = FwFilterManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present", params={"description": "bad", "action": "pass", "interface": "lan"}
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="firewall/filter/addRule",
            validations={"rule.action": "required"},
        )

        mgr = FwFilterManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(
                state="present", params={"description": "bad", "action": "pass", "interface": "lan"}
            )

        assert exc_info.value.validations == {"rule.action": "required"}


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """Tests for AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        """Two rules with same composite keys -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Allow HTTPS",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
            {
                "uuid": "uuid-2",
                "description": "Allow HTTPS",
                "action": "block",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        ]

        mgr = FwFilterManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "Allow HTTPS",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                    "action": "pass",
                },
            )

        assert len(exc_info.value.uuids) == 2
        assert "uuid-1" in exc_info.value.uuids
        assert "uuid-2" in exc_info.value.uuids
        assert exc_info.value.match_keys == {
            "description": "Allow HTTPS",
            "interface": "lan",
            "direction": "in",
            "protocol": "TCP",
        }

    async def test_no_ambiguity_different_composite_key(self, mock_client: AsyncMock) -> None:
        """Two rules with same description but different interface -> no ambiguity."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Allow HTTPS",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
            {
                "uuid": "uuid-2",
                "description": "Allow HTTPS",
                "interface": "wan",
                "direction": "in",
                "protocol": "TCP",
            },
        ]

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Allow HTTPS",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "action": "pass",
            },
        )
        # Should match uuid-1 only, no ambiguity
        assert result.action == "noop"

    async def test_uuid_escape_hatch_bypasses_find(self, mock_client: AsyncMock) -> None:
        """ensure(uuid=) bypasses _find_existing entirely."""
        mock_client.get.return_value = {
            "rule": {
                "description": "Allow HTTPS",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        }

        mgr = FwFilterManager(mock_client)
        result = await mgr.ensure(
            state="present",
            uuid="uuid-known",
            params={
                "description": "Allow HTTPS",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "action": "pass",
            },
        )

        # Should NOT call search — went straight to get by UUID
        mock_client.search.assert_not_awaited()
        assert result.action == "noop"

    async def test_ambiguous_match_on_delete(self, mock_client: AsyncMock) -> None:
        """Delete with ambiguous match -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "dup",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
            {
                "uuid": "uuid-2",
                "description": "dup",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
            },
        ]

        mgr = FwFilterManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "description": "dup",
                    "interface": "lan",
                    "direction": "in",
                    "protocol": "TCP",
                },
            )


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_invalid_action_enum_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """action='drop' fails enum validation (valid: pass/block/reject)."""
        mgr = FwFilterManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "test", "action": "drop", "interface": "lan"},
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = FwFilterManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"action": "pass", "interface": "lan"})
        mock_client.create.assert_not_awaited()
