# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.acme.certificate — AcmeCertificate."""

from __future__ import annotations

import pytest

from opnsense.models.acme.certificate import AcmeCertificate


class TestAcmeCertificate:
    """AcmeCertificate frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AcmeCertificate(name="fw.example.com").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = AcmeCertificate(name="fw.example.com")
        assert obj.name == "fw.example.com"

    def test_defaults(self) -> None:
        obj = AcmeCertificate(name="fw.example.com")
        assert obj.enabled == "1"
        assert obj.keyLength == "key_4096"
        assert obj.ocsp == "0"
        assert obj.autoRenewal == "1"
        assert obj.renewInterval == "60"
        assert obj.aliasmode == "none"
        assert obj.account == ""
        assert obj.validationMethod == ""
        assert obj.restartActions == ""
        assert obj.certRefId == ""
        assert obj.uuid == ""

    def test_reference_fields(self) -> None:
        obj = AcmeCertificate(
            name="fw.example.com",
            account="acct-uuid",
            validationMethod="val-uuid",
            restartActions="act-uuid",
        )
        assert obj.account == "acct-uuid"
        assert obj.validationMethod == "val-uuid"
        assert obj.restartActions == "act-uuid"
