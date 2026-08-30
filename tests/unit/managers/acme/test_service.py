# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.service.AcmeServiceManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.acme.service import AcmeServiceManager


@pytest.mark.asyncio
class TestServiceEnsure:
    async def test_reconfigure_always_acts(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mock_client.post.return_value = {"status": "ok"}
        mgr = AcmeServiceManager(mock_client)
        result = await mgr.ensure("reconfigured")
        assert result.changed is True
        assert result.action == "reconfigured"
        mock_client.post.assert_awaited_once_with("acmeclient/service/reconfigure", {}, timeout=60)

    async def test_running_noop_when_already_running(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "running"}
        mgr = AcmeServiceManager(mock_client)
        result = await mgr.ensure("running")
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_invalid_state_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeServiceManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("frobnicated")


@pytest.mark.asyncio
class TestConfigtest:
    async def test_configtest_returns_result(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"result": "OK"}
        mgr = AcmeServiceManager(mock_client)
        assert await mgr.configtest() == "OK"
        mock_client.get.assert_awaited_once_with("acmeclient/service/configtest")

    async def test_configtest_failure_logs_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.get.side_effect = OpnsenseServerError(
            message="boom", endpoint="acmeclient/service/configtest"
        )
        mgr = AcmeServiceManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.acme.service"),
            pytest.raises(OpnsenseServerError),
        ):
            await mgr.configtest()
        assert any("configtest failed" in r.message for r in caplog.records)
