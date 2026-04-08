"""Unit tests for opnsense.managers.ts_rule.TsRuleManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError, FieldValidationError, OpnsenseValidationError
from opnsense.managers.ts_rule import TsRuleManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
                "enabled": "1",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when rule matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
                "enabled": "1",
            },
        ]

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
                "enabled": "1",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when direction differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
                "enabled": "1",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
                "enabled": "1",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "out",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_rule(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule exists -> delete + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
            },
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": "nonexistent",
                "interface": "lan",
                "proto": "ip",
            },
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Test rule",
                "interface": "lan",
                "proto": "tcp",
            },
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid rule", endpoint="trafficshaper/settings/addRule"
        )

        mgr = TsRuleManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "description": "bad",
                    "interface": "lan",
                    "proto": "tcp",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="trafficshaper/settings/addRule",
            validations={"rule.proto": "required"},
        )

        mgr = TsRuleManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "bad",
                    "interface": "lan",
                    "proto": "tcp",
                },
            )

        assert exc_info.value.validations == {"rule.proto": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_invalid_proto_enum_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """proto='icmp' fails enum validation (valid: ip, ip4, ip6, udp, tcp)."""
        mgr = TsRuleManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "test",
                    "interface": "lan",
                    "proto": "icmp",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_direction_enum_raises(self, mock_client: AsyncMock) -> None:
        """direction='both' fails enum validation."""
        mgr = TsRuleManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "test",
                    "interface": "lan",
                    "direction": "both",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = TsRuleManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"interface": "lan", "proto": "tcp"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_interface_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'interface' raises FieldValidationError."""
        mgr = TsRuleManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"description": "test"})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """Tests for AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        """Two rules with same composite keys -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
            },
            {
                "uuid": "uuid-2",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "out",
            },
        ]

        mgr = TsRuleManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "description": "Shape VoIP",
                    "interface": "lan",
                    "proto": "udp",
                    "direction": "in",
                },
            )

        assert len(exc_info.value.uuids) == 2
        assert "uuid-1" in exc_info.value.uuids
        assert "uuid-2" in exc_info.value.uuids
        assert exc_info.value.match_keys == {
            "description": "Shape VoIP",
            "interface": "lan",
            "proto": "udp",
        }

    async def test_no_ambiguity_different_composite_key(self, mock_client: AsyncMock) -> None:
        """Two rules with same description but different interface -> no ambiguity."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
            },
            {
                "uuid": "uuid-2",
                "description": "Shape VoIP",
                "interface": "wan",
                "proto": "udp",
            },
        ]

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
            },
        )
        # Should match uuid-1 only, no ambiguity
        assert result.action == "noop"

    async def test_uuid_escape_hatch_bypasses_find(self, mock_client: AsyncMock) -> None:
        """ensure(uuid=) bypasses _find_existing entirely."""
        mock_client.get.return_value = {
            "rule": {
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
            },
        }

        mgr = TsRuleManager(mock_client)
        result = await mgr.ensure(
            state="present",
            uuid="uuid-known",
            params={
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
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
                "proto": "tcp",
            },
            {
                "uuid": "uuid-2",
                "description": "dup",
                "interface": "lan",
                "proto": "tcp",
            },
        ]

        mgr = TsRuleManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "description": "dup",
                    "interface": "lan",
                    "proto": "tcp",
                },
            )


@pytest.mark.asyncio
class TestSearchOverride:
    """Verify list() uses the plural searchRules endpoint."""

    async def test_list_uses_search_rules_plural(self, mock_client: AsyncMock) -> None:
        """list() must call trafficshaper/settings/searchRules (plural)."""
        mock_client.search.return_value = []

        mgr = TsRuleManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with(
            "trafficshaper/settings/searchRules", search_phrase=""
        )

    async def test_list_passes_search_phrase(self, mock_client: AsyncMock) -> None:
        """list(search_phrase=) is forwarded to the client."""
        mock_client.search.return_value = []

        mgr = TsRuleManager(mock_client)
        await mgr.list(search_phrase="voip")

        mock_client.search.assert_awaited_once_with(
            "trafficshaper/settings/searchRules", search_phrase="voip"
        )
