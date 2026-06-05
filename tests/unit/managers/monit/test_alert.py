# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.monit.alert.MonitAlertManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseError, OpnsenseValidationError
from opnsense.managers.monit.alert import MonitAlertManager, _normalize_events


class TestNormalizeEvents:
    """The events multi-select helper accepts list/tuple/set/str -> CSV."""

    def test_string_passes_through(self) -> None:
        assert _normalize_events("connection,timeout") == "connection,timeout"

    def test_list_joined_with_comma(self) -> None:
        assert _normalize_events(["connection", "timeout"]) == "connection,timeout"

    def test_tuple_joined(self) -> None:
        assert _normalize_events(("a", "b")) == "a,b"

    def test_empty_list_yields_empty_string(self) -> None:
        assert _normalize_events([]) == ""

    def test_none_yields_empty_string(self) -> None:
        assert _normalize_events(None) == ""


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_alert(self, mock_client: AsyncMock) -> None:
        """ensure present when alert does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"recipient": "noc@example.com", "enabled": "1"},
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("monit/service/reconfigure", timeout=None)

    async def test_events_list_normalized_to_csv(self, mock_client: AsyncMock) -> None:
        """events list is coerced to a comma-separated string before create."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitAlertManager(mock_client)
        await mgr.ensure(
            state="present",
            params={
                "recipient": "noc@example.com",
                "events": ["connection", "timeout", "status"],
            },
        )

        sent = mock_client.create.await_args.args[2]
        assert sent["events"] == "connection,timeout,status"

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when alert exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "recipient": "noc@example.com", "enabled": "1"},
        ]

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"recipient": "noc@example.com", "enabled": "1"},
        )

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-existing"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when alert differs -> update + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "recipient": "noc@example.com", "enabled": "0"},
        ]
        mock_client.get.return_value = {
            "alert": {"uuid": "uuid-existing", "recipient": "noc@example.com", "enabled": "0"},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"recipient": "noc@example.com", "enabled": "1"},
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("monit/service/reconfigure", timeout=None)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_alert(self, mock_client: AsyncMock) -> None:
        """ensure absent when alert exists -> delete + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "recipient": "noc@example.com"},
        ]
        mock_client.get.return_value = {
            "alert": {"uuid": "uuid-existing", "recipient": "noc@example.com"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(state="absent", params={"recipient": "noc@example.com"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when alert does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(state="absent", params={"recipient": "gone@example.com"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no API calls."""
        mock_client.search.return_value = []

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"recipient": "noc@example.com"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Alert entity suffix."""

    async def test_search_uses_search_alert(self, mock_client: AsyncMock) -> None:
        """list() calls search endpoint with Alert suffix."""
        mock_client.search.return_value = []

        mgr = MonitAlertManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with("monit/settings/searchAlert", search_phrase="")


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on MonitAlertManager."""

    async def test_recipient_redacted(self) -> None:
        """MonitAlertManager redacts recipient (PII)."""
        assert "recipient" in MonitAlertManager.REDACT_FIELDS

    async def test_create_redacts_recipient_in_result(self, mock_client: AsyncMock) -> None:
        """ensure present create -> recipient is redacted in after dict."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitAlertManager(mock_client)
        result = await mgr.ensure(state="present", params={"recipient": "noc@example.com"})

        assert result.after is not None
        assert result.after["recipient"] == "<REDACTED:recipient>"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When create() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad recipient", endpoint="monit/settings/addAlert"
        )

        mgr = MonitAlertManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"recipient": "noc@example.com"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When delete() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "recipient": "noc@example.com"},
        ]
        mock_client.get.return_value = {
            "alert": {"uuid": "uuid-1", "recipient": "noc@example.com"},
        }
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = MonitAlertManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(state="absent", params={"recipient": "noc@example.com"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_recipient_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'recipient' raises FieldValidationError before API call."""
        mgr = MonitAlertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"enabled": "1"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_bool_str_raises(self, mock_client: AsyncMock) -> None:
        """Non-bool_str 'enabled' raises FieldValidationError before API call."""
        mgr = MonitAlertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"recipient": "noc@example.com", "enabled": "yes"})
        mock_client.create.assert_not_awaited()
