# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.acme.validation — AcmeValidation."""

from __future__ import annotations

import pytest

from opnsense.models.acme.validation import AcmeValidation


class TestAcmeValidation:
    """AcmeValidation frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AcmeValidation(name="cloudflare-dns").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = AcmeValidation(name="cloudflare-dns")
        assert obj.name == "cloudflare-dns"

    def test_defaults(self) -> None:
        obj = AcmeValidation(name="cloudflare-dns")
        assert obj.enabled == "1"
        assert obj.method == "dns01"
        assert obj.http_service == "opnsense"
        assert obj.http_opn_autodiscovery == "1"
        assert obj.tlsalpn_service == "acme"
        assert obj.dns_service == ""
        assert obj.dns_sleep == "0"
        assert obj.dns_cf_token == ""
        assert obj.dns_cf_account_id == ""
        assert obj.uuid == ""

    def test_cloudflare_fields(self) -> None:
        obj = AcmeValidation(
            name="cloudflare-dns",
            dns_service="dns_cf",
            dns_cf_token="tok",
            dns_cf_account_id="acct",
        )
        assert obj.dns_service == "dns_cf"
        assert obj.dns_cf_token == "tok"
        assert obj.dns_cf_account_id == "acct"
