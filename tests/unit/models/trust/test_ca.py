# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.trust_ca — TrustCa."""

from __future__ import annotations

import pytest

from opnsense.models.trust_ca import TrustCa


class TestTrustCa:
    """TrustCa frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            TrustCa(descr="Root CA").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = TrustCa(descr="Root CA")
        assert obj.descr == "Root CA"

    def test_defaults(self) -> None:
        obj = TrustCa(descr="Root CA")
        assert obj.action == "internal"
        assert obj.key_type == "2048"
        assert obj.digest == "sha256"
        assert obj.lifetime == "825"
        assert obj.commonname == ""
        assert obj.country == ""
        assert obj.state == ""
        assert obj.city == ""
        assert obj.organization == ""
        assert obj.email == ""
        assert obj.crt_payload == ""
        assert obj.prv_payload == ""
        assert obj.caref == ""
        assert obj.uuid == ""
