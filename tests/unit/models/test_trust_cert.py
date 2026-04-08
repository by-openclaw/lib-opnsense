# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.trust_cert — TrustCert."""

from __future__ import annotations

import pytest

from opnsense.models.trust_cert import TrustCert


class TestTrustCert:
    """TrustCert frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            TrustCert(descr="Web Cert").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = TrustCert(descr="Web Cert")
        assert obj.descr == "Web Cert"

    def test_defaults(self) -> None:
        obj = TrustCert(descr="Web Cert")
        assert obj.caref == ""
        assert obj.action == "internal"
        assert obj.key_type == "2048"
        assert obj.digest == "sha256"
        assert obj.cert_type == "server_cert"
        assert obj.lifetime == "397"
        assert obj.commonname == ""
        assert obj.altnames_dns == ""
        assert obj.altnames_ip == ""
        assert obj.altnames_email == ""
        assert obj.altnames_uri == ""
        assert obj.country == ""
        assert obj.state == ""
        assert obj.city == ""
        assert obj.organization == ""
        assert obj.email == ""
        assert obj.crt_payload == ""
        assert obj.prv_payload == ""
        assert obj.csr_payload == ""
        assert obj.uuid == ""
