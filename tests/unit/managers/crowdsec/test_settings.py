# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.crowdsec.settings.CrowdSecSettingsManager.

Singleton pattern: ``crowdsec/general/get`` returns the config under a
top-level ``general`` key, which the base manager unwraps for diffing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.crowdsec.settings import CrowdSecSettingsManager

# Fabricated value, never a real key — long enough to prove redaction strips it.
FAKE_ENROLL_KEY = "cvbnmqwertyuiop1234567890"  # pragma: allowlist secret

# Shape captured live from OPNsense 26.1.9 (docs/api/data/26.1.9/).
LIVE = {
    "general": {
        "agent_enabled": "1",
        "lapi_enabled": "1",
        "firewall_bouncer_enabled": "1",
        "lapi_manual_configuration": "0",
        "lapi_listen_address": "127.0.0.1",
        "lapi_listen_port": "8080",
        "rules_enabled": "1",
        "rules_log": "1",
        "rules_tag": "",
        "enroll_key": FAKE_ENROLL_KEY,
        "crowdsec_firewall_verbose": "0",
    }
}


@pytest.mark.asyncio
class TestGet:
    async def test_get_unwraps_general(self, mock_client: AsyncMock) -> None:
        """get() unwraps the top-level 'general' key."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        result = await mgr.get()
        assert result["lapi_listen_address"] == "127.0.0.1"
        assert result["firewall_bouncer_enabled"] == "1"
        mock_client.get.assert_awaited_once_with("crowdsec/general/get")

    async def test_get_returns_body_when_key_absent(self, mock_client: AsyncMock) -> None:
        """get() falls back to the whole body when 'general' is missing."""
        mock_client.get.return_value = {}
        mgr = CrowdSecSettingsManager(mock_client)
        assert await mgr.get() == {}


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        """No drift -> noop, and nothing is POSTed."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        result = await mgr.ensure("present", {"firewall_bouncer_enabled": "1"})
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_updates_when_drifted(self, mock_client: AsyncMock) -> None:
        """Drift -> POST to crowdsec/general/set."""
        after = {"general": dict(LIVE["general"], lapi_manual_configuration="1")}
        mock_client.get.side_effect = [LIVE, after]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = CrowdSecSettingsManager(mock_client)
        result = await mgr.ensure("present", {"lapi_manual_configuration": "1"})
        assert result.changed is True
        assert result.action == "updated"
        endpoint = mock_client.post.await_args[0][0]
        assert endpoint == "crowdsec/general/set"

    async def test_check_mode_does_not_post(self, mock_client: AsyncMock) -> None:
        """check_mode reports the change without performing it."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        result = await mgr.ensure("present", {"lapi_manual_configuration": "1"}, check_mode=True)
        assert result.changed is True
        mock_client.post.assert_not_awaited()


@pytest.mark.asyncio
class TestRedaction:
    async def test_enroll_key_is_redacted(self, mock_client: AsyncMock) -> None:
        """enroll_key must never appear in an EnsureResult.

        It is a live console credential returned in plaintext by GET; the whole
        reason this manager declares REDACT_FIELDS.
        """
        after = {"general": dict(LIVE["general"], rules_tag="edge")}
        mock_client.get.side_effect = [LIVE, after]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = CrowdSecSettingsManager(mock_client)
        result = await mgr.ensure("present", {"rules_tag": "edge"})
        assert FAKE_ENROLL_KEY not in str(result.before)
        assert FAKE_ENROLL_KEY not in str(result.after)


@pytest.mark.asyncio
class TestValidation:
    async def test_rejects_non_ip_listen_address(self, mock_client: AsyncMock) -> None:
        """lapi_listen_address is validated as an IP."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"lapi_listen_address": "not-an-ip"})

    async def test_rejects_out_of_range_port(self, mock_client: AsyncMock) -> None:
        """lapi_listen_port is validated as a port."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"lapi_listen_port": "99999"})

    async def test_rejects_non_alphanumeric_rules_tag(self, mock_client: AsyncMock) -> None:
        """rules_tag is alphanumeric-only per the API's own validation message."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"rules_tag": "has-a-hyphen"})

    async def test_rejects_non_boolean_toggle(self, mock_client: AsyncMock) -> None:
        """Boolean toggles only accept '0'/'1'."""
        mock_client.get.return_value = LIVE
        mgr = CrowdSecSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"firewall_bouncer_enabled": "yes"})
