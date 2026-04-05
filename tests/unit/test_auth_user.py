"""Unit tests for opnsense.managers.auth_user.AuthUserManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.auth_user import AuthUserManager
from opnsense.models.base import EnsureResult


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_user(self, mock_client: AsyncMock) -> None:
        """ensure present when user does not exist -> create."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "svc-test", "email": "test@example.com"},
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when user exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "svc-test", "email": "test@example.com"},
        ]

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "svc-test", "email": "test@example.com"},
        )

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-existing"
        mock_client.create.assert_not_awaited()
        mock_client.update.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when user exists but email differs -> update."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "svc-test", "email": "old@example.com"},
        ]
        mock_client.get.return_value = {
            "user": {"uuid": "uuid-existing", "name": "svc-test", "email": "old@example.com"},
        }
        mock_client.update.return_value = {"result": "saved"}

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "svc-test", "email": "new@example.com"},
        )

        assert result.changed is True
        assert result.action == "updated"
        assert result.uuid == "uuid-existing"

    async def test_create_redacts_password_in_result(self, mock_client: AsyncMock) -> None:
        """ensure present create -> password is redacted in after dict."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "svc-test", "password": "s3cret"},
        )

        assert result.changed is True
        assert result.after is not None
        assert result.after["password"] == "<REDACTED:password>"


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_user(self, mock_client: AsyncMock) -> None:
        """ensure absent when user exists -> delete."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "svc-test"},
        ]
        mock_client.get.return_value = {
            "user": {"uuid": "uuid-existing", "name": "svc-test"},
        }
        mock_client.delete.return_value = {"result": "deleted"}

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "svc-test"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when user does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "nonexistent"},
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no create API call."""
        mock_client.search.return_value = []

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "svc-test"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode delete -> changed=True but no delete API call."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "svc-test"},
        ]
        mock_client.get.return_value = {
            "user": {"uuid": "uuid-existing", "name": "svc-test"},
        }

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "svc-test"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()

    async def test_check_mode_noop_stays_noop(self, mock_client: AsyncMock) -> None:
        """check_mode on already matching state -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "svc-test"},
        ]

        mgr = AuthUserManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "svc-test"},
            check_mode=True,
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on AuthUserManager."""

    async def test_redact_fields_defined(self) -> None:
        """AuthUserManager has the expected redact fields."""
        assert "password" in AuthUserManager.REDACT_FIELDS
        assert "otp_seed" in AuthUserManager.REDACT_FIELDS
        assert "scrambled_password" in AuthUserManager.REDACT_FIELDS
        assert "authorizedkeys" in AuthUserManager.REDACT_FIELDS


@pytest.mark.asyncio
class TestInvalidState:
    """Tests for invalid state argument."""

    async def test_invalid_state_raises_value_error(self, mock_client: AsyncMock) -> None:
        mgr = AuthUserManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"name": "test"})
