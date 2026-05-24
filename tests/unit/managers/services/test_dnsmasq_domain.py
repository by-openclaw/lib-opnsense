# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.services.dnsmasq_domain.DnsmasqDomainManager.

Covers ADR ``lib/python/0001 §10.2`` mandatory test set.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseServerError,
    OpnsenseValidationError,
)
from opnsense.managers.services.dnsmasq_domain import DnsmasqDomainManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_creates_when_missing(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqDomainManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"domain": "internal.example.com", "ip": "10.0.0.53"},
        )
        assert r.changed is True
        assert r.action == "created"
        # Verify payload key is 'domainoverride'
        endpoint, payload_key, params = mock_client.create.await_args.args
        assert payload_key == "domainoverride"

    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
            }
        ]
        mgr = DnsmasqDomainManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"domain": "internal.example.com", "ip": "10.0.0.53"},
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_updates_when_descr_changes(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-exists",
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
                "descr": "old",
            }
        ]
        mock_client.get.return_value = {
            "domainoverride": {
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
                "descr": "old",
            }
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqDomainManager(mock_client)
        r = await mgr.ensure(
            "present",
            {
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
                "descr": "new",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_check_mode_does_not_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqDomainManager(mock_client)
        r = await mgr.ensure(
            "present",
            {"domain": "internal.example.com", "ip": "10.0.0.53"},
            check_mode=True,
        )
        assert r.changed is True
        assert r.action == "created"
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_deletes_when_exists(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-gone",
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
            }
        ]
        mock_client.get.return_value = {
            "domainoverride": {
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
            }
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = DnsmasqDomainManager(mock_client)
        r = await mgr.ensure("absent", {"domain": "internal.example.com", "ip": "10.0.0.53"})
        assert r.changed is True
        assert r.action == "deleted"

    async def test_noop_when_already_gone(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DnsmasqDomainManager(mock_client)
        r = await mgr.ensure("absent", {"domain": "internal.example.com", "ip": "10.0.0.53"})
        assert r.changed is False
        assert r.action == "noop"


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_domain(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqDomainManager(mock_client)
        with pytest.raises(FieldValidationError, match="domain"):
            await mgr.ensure("present", {"ip": "10.0.0.53"})

    async def test_missing_ip(self, mock_client: AsyncMock) -> None:
        mgr = DnsmasqDomainManager(mock_client)
        with pytest.raises(FieldValidationError, match="ip"):
            await mgr.ensure("present", {"domain": "internal.example.com"})


@pytest.mark.asyncio
class TestAmbiguousMatch:
    async def test_raises_when_multiple_match(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "domain": "dup.example.com", "ip": "10.0.0.1"},
            {"uuid": "u2", "domain": "dup.example.com", "ip": "10.0.0.1"},
        ]
        mgr = DnsmasqDomainManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure("present", {"domain": "dup.example.com", "ip": "10.0.0.1"})
        assert set(exc_info.value.uuids) == {"u1", "u2"}


@pytest.mark.asyncio
class TestErrorPropagation:
    async def test_create_failure_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseServerError("boom")
        mgr = DnsmasqDomainManager(mock_client)
        with pytest.raises(OpnsenseServerError):
            await mgr.ensure("present", {"domain": "x.example.com", "ip": "10.0.0.1"})

    async def test_server_validation_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError("rejected")
        mgr = DnsmasqDomainManager(mock_client)
        with pytest.raises(OpnsenseValidationError):
            await mgr.ensure("present", {"domain": "x.example.com", "ip": "10.0.0.1"})
