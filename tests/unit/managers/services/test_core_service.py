# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for CoreServiceManager — registry lookup + start/stop/restart by name."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.services.core_service import CoreServiceManager

ROWS = {
    "rows": [
        {"id": "ntpd", "name": "ntpd", "running": 0, "locked": 0},
        {"id": "openssh", "name": "openssh", "running": 1, "locked": 0},
    ]
}


@pytest.fixture
def client() -> AsyncMock:
    c = AsyncMock(spec=OpnsenseClient)
    c._base_url = "https://opnsense.example.com"
    return c


@pytest.mark.asyncio
class TestCoreService:
    async def test_status_from_registry(self, client: AsyncMock) -> None:
        client.get.return_value = ROWS
        mgr = CoreServiceManager(client)
        assert await mgr.status("ntpd") == "stopped"
        assert await mgr.status("openssh") == "running"
        assert await mgr.status("nope") == "unknown"
        client.get.assert_awaited_with("core/service/search")

    async def test_stopped_noop_when_stopped_or_unknown(self, client: AsyncMock) -> None:
        client.get.return_value = ROWS
        mgr = CoreServiceManager(client)
        assert (await mgr.ensure("ntpd", "stopped")).action == "noop"
        assert (await mgr.ensure("nope", "stopped")).action == "noop"
        client.post.assert_not_awaited()

    async def test_stop_running_daemon(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            ROWS,
            {"rows": [{"id": "openssh", "name": "openssh", "running": 0}]},
        ]
        client.post.return_value = {"result": "ok"}
        r = await CoreServiceManager(client).ensure("openssh", "stopped")
        assert r.changed is True and r.action == "stopped" and r.after == {"status": "stopped"}
        client.post.assert_awaited_once_with("core/service/stop/openssh", data={})

    async def test_start_and_restart(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            ROWS,
            {"rows": [{"id": "ntpd", "name": "ntpd", "running": 1}]},
            ROWS,
            ROWS,
        ]
        client.post.return_value = {"result": "ok"}
        mgr = CoreServiceManager(client)
        assert (await mgr.ensure("ntpd", "running")).action == "started"
        assert (await mgr.ensure("openssh", "restarted")).action == "restarted"
        assert [c.args[0] for c in client.post.await_args_list] == [
            "core/service/start/ntpd",
            "core/service/restart/openssh",
        ]

    async def test_check_mode(self, client: AsyncMock) -> None:
        client.get.return_value = ROWS
        r = await CoreServiceManager(client).ensure("openssh", "stopped", check_mode=True)
        assert r.changed is True and r.after == {"status": "stopped"}
        client.post.assert_not_awaited()

    async def test_error_propagates_and_invalid_state(self, client: AsyncMock) -> None:
        client.get.return_value = ROWS
        client.post.side_effect = OpnsenseServerError("boom")
        with pytest.raises(OpnsenseServerError):
            await CoreServiceManager(client).ensure("openssh", "stopped")
        with pytest.raises(ValueError):
            await CoreServiceManager(client).ensure("openssh", "reloaded")
