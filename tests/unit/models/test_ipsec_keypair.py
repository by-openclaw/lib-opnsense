# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.ipsec_keypair -- IpsecKeypair."""

from __future__ import annotations

import pytest

from opnsense.models.ipsec_keypair import IpsecKeypair


class TestIpsecKeypair:
    """IpsecKeypair frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            IpsecKeypair(name="kp0").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = IpsecKeypair(name="kp0")
        assert obj.name == "kp0"

    def test_defaults(self) -> None:
        obj = IpsecKeypair(name="kp0")
        assert obj.keyType == "RSA"
        assert obj.publicKey == ""
        assert obj.privateKey == ""
        assert obj.keySize == ""
        assert obj.uuid == ""

    def test_all_fields(self) -> None:
        obj = IpsecKeypair(
            name="site-a-keypair",
            keyType="RSA",
            publicKey="pubkey-pem",
            privateKey="privkey-pem",
            keySize="4096",
            uuid="uuid-1",
        )
        assert obj.name == "site-a-keypair"
        assert obj.keyType == "RSA"
        assert obj.publicKey == "pubkey-pem"
        assert obj.privateKey == "privkey-pem"
        assert obj.uuid == "uuid-1"
