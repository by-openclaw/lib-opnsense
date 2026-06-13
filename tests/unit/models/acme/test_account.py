# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.acme.account — AcmeAccount."""

from __future__ import annotations

import pytest

from opnsense.models.acme.account import AcmeAccount


class TestAcmeAccount:
    """AcmeAccount frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AcmeAccount(name="letsencrypt-prod").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = AcmeAccount(name="letsencrypt-prod")
        assert obj.name == "letsencrypt-prod"

    def test_defaults(self) -> None:
        obj = AcmeAccount(name="letsencrypt-prod")
        assert obj.enabled == "1"
        assert obj.ca == "letsencrypt"
        assert obj.email == ""
        assert obj.custom_ca == ""
        assert obj.eab_kid == ""
        assert obj.eab_hmac == ""
        assert obj.key == ""
        assert obj.statusCode == ""
        assert obj.statusLastUpdate == ""
        assert obj.id == ""
        assert obj.uuid == ""
