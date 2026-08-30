# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.validations.AcmeValidationManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.acme.validations import AcmeValidationManager


@pytest.mark.asyncio
class TestEnsure:
    async def test_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mgr = AcmeValidationManager(mock_client)
        result = await mgr.ensure(
            "present",
            {
                "name": "cloudflare-dns",
                "method": "dns01",
                "dns_service": "dns_cf",
                "dns_cf_token": "tok",
            },
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_not_awaited()

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "name": "cloudflare-dns", "method": "dns01"},
        ]
        mgr = AcmeValidationManager(mock_client)
        result = await mgr.ensure("present", {"name": "cloudflare-dns", "method": "dns01"})
        assert result.action == "noop"

    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "u1", "name": "cloudflare-dns"}]
        mock_client.get.return_value = {"validation": {"uuid": "u1", "name": "cloudflare-dns"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mgr = AcmeValidationManager(mock_client)
        result = await mgr.ensure("absent", {"name": "cloudflare-dns"})
        assert result.action == "deleted"


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_name_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeValidationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"method": "dns01"})

    async def test_invalid_method_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeValidationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"name": "x", "method": "dns99"})

    async def test_invalid_http_service_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeValidationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"name": "x", "http_service": "nginx"})


class TestRedactFields:
    def test_cloudflare_secrets_redacted(self) -> None:
        assert "dns_cf_token" in AcmeValidationManager.REDACT_FIELDS
        assert "dns_cf_key" in AcmeValidationManager.REDACT_FIELDS

    @pytest.mark.asyncio
    async def test_token_redacted_in_after(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mgr = AcmeValidationManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"name": "cloudflare-dns", "dns_service": "dns_cf", "dns_cf_token": "s3cret"},
        )
        assert result.after is not None
        assert result.after["dns_cf_token"] == "<REDACTED:dns_cf_token>"

    @pytest.mark.asyncio
    async def test_unknown_provider_field_passes_through(self, mock_client: AsyncMock) -> None:
        """A non-declared DNS provider field is forwarded untouched (not rejected)."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mgr = AcmeValidationManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"name": "route53", "dns_service": "dns_aws", "dns_aws_id": "AKIA..."},
        )
        assert result.changed is True
        # field was passed straight to create() — params is the 3rd positional arg
        sent = mock_client.create.call_args.args[2]
        assert sent["dns_aws_id"] == "AKIA..."
