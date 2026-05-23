# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.dnsmasq_host.DnsmasqHostManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
    OpnsenseValidationError,
)
from opnsense.managers.services.dnsmasq_host import DnsmasqHostManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_creates_when_missing(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DnsmasqHostManager(mock_client)
        result = await mgr.ensure(
            "present",
            {
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
            },
        )
        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.reconfigure.assert_awaited_once_with("dnsmasq/service/reconfigure", timeout=60)

    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
            }
        ]
        mgr = DnsmasqHostManager(mock_client)
        result = await mgr.ensure(
            "present",
            {
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
            },
        )
        assert result.changed is False
        assert result.action == "noop"

    async def test_updates_when_drifted(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
            }
        ]
        mock_client.get.return_value = {
            "host": {
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
            }
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DnsmasqHostManager(mock_client)
        result = await mgr.ensure(
            "present",
            {
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.51",  # new IP
            },
        )
        assert result.changed is True
        assert result.action == "updated"

    async def test_check_mode_does_not_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqHostManager(mock_client)
        result = await mgr.ensure(
            "present",
            {
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_deletes_when_exists(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-gone", "host": "printer-01", "domain": "lan.example.com"}
        ]
        mock_client.get.return_value = {"host": {"host": "printer-01", "domain": "lan.example.com"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DnsmasqHostManager(mock_client)
        result = await mgr.ensure("absent", {"host": "printer-01", "domain": "lan.example.com"})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop_when_already_gone(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqHostManager(mock_client)
        result = await mgr.ensure("absent", {"host": "printer-01", "domain": "lan.example.com"})
        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_required_host(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqHostManager(mock_client)
        with pytest.raises(FieldValidationError, match="host"):
            await mgr.ensure("present", {"domain": "lan.example.com", "ip": "10.0.0.50"})
        mock_client.search.assert_not_awaited()

    async def test_missing_required_domain(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqHostManager(mock_client)
        with pytest.raises(FieldValidationError, match="domain"):
            await mgr.ensure("present", {"host": "printer-01", "ip": "10.0.0.50"})
        mock_client.search.assert_not_awaited()

    async def test_invalid_bool_rejected(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqHostManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                {
                    "host": "printer-01",
                    "domain": "lan.example.com",
                    "ignore": "not-a-bool",
                },
            )


@pytest.mark.asyncio
class TestAmbiguousMatch:
    async def test_raises_when_multiple_match(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "host": "dup", "domain": "lan.example.com"},
            {"uuid": "uuid-2", "host": "dup", "domain": "lan.example.com"},
        ]
        mgr = DnsmasqHostManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                {"host": "dup", "domain": "lan.example.com", "ip": "10.0.0.99"},
            )
        assert set(exc_info.value.uuids) == {"uuid-1", "uuid-2"}


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_create_failure_logs_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqHostManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseServerError),
        ):
            await mgr.ensure(
                "present",
                {"host": "p", "domain": "d", "ip": "10.0.0.1"},
            )

    async def test_server_validation_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError("rejected")
        mgr = DnsmasqHostManager(mock_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure(
                "present",
                {"host": "p", "domain": "d", "ip": "10.0.0.1"},
            )
