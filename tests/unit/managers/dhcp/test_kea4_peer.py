"""Unit tests for opnsense.managers.kea4_peer.Kea4PeerManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.dhcp.kea4_peer import Kea4PeerManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_peer(self, mock_client: AsyncMock) -> None:
        """ensure present when peer does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "peer-standby",
                "role": "primary",
                "url": "https://peer.example.com:8000/",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when peer matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "peer-standby",
                "role": "primary",
                "url": "https://peer.example.com:8000/",
            },
        ]

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "peer-standby",
                "role": "primary",
                "url": "https://peer.example.com:8000/",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when role differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "peer-standby",
                "role": "primary",
                "url": "https://peer.example.com:8000/",
            },
        ]
        mock_client.get.return_value = {
            "peer": {
                "uuid": "uuid-existing",
                "name": "peer-standby",
                "role": "primary",
                "url": "https://peer.example.com:8000/",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "peer-standby",
                "role": "standby",
                "url": "https://peer.example.com:8000/",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_peer(self, mock_client: AsyncMock) -> None:
        """ensure absent when peer exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "peer-standby"},
        ]
        mock_client.get.return_value = {
            "peer": {"uuid": "uuid-existing", "name": "peer-standby"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "peer-standby"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when peer does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "peer-standby",
                "url": "https://peer.example.com:8000/",
            },
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "peer-standby"},
        ]
        mock_client.get.return_value = {
            "peer": {"uuid": "uuid-1", "name": "peer-standby"},
        }

        mgr = Kea4PeerManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "peer-standby"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally -- errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid peer", endpoint="kea/dhcpv4/addPeer"
        )

        mgr = Kea4PeerManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "name": "bad-peer",
                    "url": "https://peer.example.com:8000/",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "peer-standby"},
        ]
        mock_client.get.return_value = {
            "peer": {"uuid": "uuid-1", "name": "peer-standby"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="kea/dhcpv4/delPeer"
        )

        mgr = Kea4PeerManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"name": "peer-standby"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_name_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4PeerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"role": "primary", "url": "https://peer.example.com:8000/"},
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_url_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4PeerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "peer-standby"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_role_enum_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4PeerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "name": "peer-standby",
                    "role": "backup",
                    "url": "https://peer.example.com:8000/",
                },
            )
        mock_client.create.assert_not_awaited()
