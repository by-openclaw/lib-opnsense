# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.acme.settings — AcmeSettings."""

from __future__ import annotations

import pytest

from opnsense.models.acme.settings import AcmeSettings


class TestAcmeSettings:
    """AcmeSettings frozen dataclass (singleton)."""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AcmeSettings().enabled = "1"  # type: ignore[misc]

    def test_defaults(self) -> None:
        obj = AcmeSettings()
        assert obj.enabled == "0"
        assert obj.autoRenewal == "1"
        assert obj.environment == ""
        assert obj.challengePort == "43580"
        assert obj.TLSchallengePort == "43581"
        assert obj.restartTimeout == "600"
        assert obj.haproxyIntegration == "0"
        assert obj.logLevel == "normal"
        assert obj.showIntro == "1"
