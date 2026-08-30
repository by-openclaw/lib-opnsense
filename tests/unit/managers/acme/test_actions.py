# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.actions.AcmeActionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.acme.actions import AcmeActionManager


@pytest.mark.asyncio
class TestEnsure:
    async def test_create_restart_gui(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mgr = AcmeActionManager(mock_client)
        result = await mgr.ensure(
            "present", {"name": "restart-webgui", "type": "configd_restart_gui"}
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_not_awaited()

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "name": "restart-webgui", "type": "configd_restart_gui"},
        ]
        mgr = AcmeActionManager(mock_client)
        result = await mgr.ensure(
            "present", {"name": "restart-webgui", "type": "configd_restart_gui"}
        )
        assert result.action == "noop"

    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "u1", "name": "restart-webgui"}]
        mock_client.get.return_value = {"action": {"uuid": "u1", "name": "restart-webgui"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mgr = AcmeActionManager(mock_client)
        result = await mgr.ensure("absent", {"name": "restart-webgui"})
        assert result.action == "deleted"


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_name_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeActionManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"type": "configd_restart_gui"})

    async def test_invalid_type_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeActionManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"name": "x", "type": "reboot_everything"})

    async def test_invalid_identity_type_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeActionManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {"name": "x", "type": "configd_upload_sftp", "sftp_identity_type": "dsa"},
            )


class TestRedactFields:
    def test_credential_fields_redacted(self) -> None:
        assert "acme_proxmoxve_tokenkey" in AcmeActionManager.REDACT_FIELDS
        assert "acme_synology_dsm_password" in AcmeActionManager.REDACT_FIELDS
