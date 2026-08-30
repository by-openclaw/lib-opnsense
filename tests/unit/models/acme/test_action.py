# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.acme.action — AcmeAction."""

from __future__ import annotations

import pytest

from opnsense.models.acme.action import AcmeAction


class TestAcmeAction:
    """AcmeAction frozen dataclass."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AcmeAction(name="restart-webgui").uuid = "changed"  # type: ignore[misc]

    def test_required_field(self) -> None:
        obj = AcmeAction(name="restart-webgui")
        assert obj.name == "restart-webgui"

    def test_defaults(self) -> None:
        obj = AcmeAction(name="restart-webgui")
        assert obj.enabled == "1"
        assert obj.type == "configd_restart_gui"
        assert obj.sftp_port == "22"
        assert obj.remote_ssh_port == "22"
        assert obj.sftp_identity_type == ""
        assert obj.remote_ssh_identity_type == ""
        assert obj.uuid == ""
