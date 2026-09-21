# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for FirmwareManager — check job, status, update/upgrade, reboot-tolerant wait."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseConnectionError, OpnsenseTimeoutError
from opnsense.managers.services.firmware import FirmwareManager


@pytest.fixture
def client() -> AsyncMock:
    c = AsyncMock(spec=OpnsenseClient)
    c._base_url = "https://opnsense.example.com"
    return c


def _status(version: str, status: str) -> dict:
    return {"product_version": version, "status": status, "upgrade_packages": []}


@pytest.mark.asyncio
class TestCheckAndStatus:
    async def test_check_runs_job_then_reads_status(self, client: AsyncMock) -> None:
        client.post.side_effect = [
            {"status": "ok"},
            {"status": "running"},
            {"status": "done", "log": "x"},
        ]
        client.get.return_value = _status("26.7", "update")
        fw = FirmwareManager(client)
        resolved = await fw.check(interval=0)
        assert resolved["status"] == "update"
        assert client.post.await_args_list[0].args[0] == "core/firmware/check"
        client.get.assert_awaited_once_with("core/firmware/status")

    async def test_check_job_timeout(self, client: AsyncMock) -> None:
        client.post.side_effect = [{"status": "ok"}] + [{"status": "running"}] * 5
        with pytest.raises(OpnsenseTimeoutError):
            await FirmwareManager(client).check(timeout=0, interval=0)


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_nothing_pending(self, client: AsyncMock) -> None:
        client.post.side_effect = [{"status": "ok"}, {"status": "done", "log": ""}]
        client.get.return_value = _status("26.7.3_11", "none")
        r = await FirmwareManager(client).ensure("updated", check_timeout=0)
        assert r.changed is False and r.action == "noop" and r.before["status"] == "none"
        assert client.post.await_count == 2  # check + upgradestatus only

    async def test_update_fires_and_waits_for_target(self, client: AsyncMock) -> None:
        client.post.side_effect = [
            {"status": "ok"},
            {"status": "done", "log": ""},
            {"status": "ok"},
        ]
        client.get.side_effect = [
            _status("26.7", "update"),  # resolved status after check
            OpnsenseConnectionError("rebooting"),  # wait: down
            _status("26.7", "none"),  # wait: still old version pre-reboot
            _status("26.7.3_11", "none"),  # wait: back on target
        ]
        fw = FirmwareManager(client)
        r = await fw.ensure("updated", target="26.7.3", check_timeout=0, wait_interval=0)
        assert r.changed is True and r.action == "updated"
        assert r.before == {"product_version": "26.7", "status": "update"}
        assert r.after["product_version"] == "26.7.3_11"
        assert client.post.await_args_list[2].args[0] == "core/firmware/update"

    async def test_upgraded_uses_update_when_only_update_pending(self, client: AsyncMock) -> None:
        client.post.side_effect = [
            {"status": "ok"},
            {"status": "done", "log": ""},
            {"status": "ok"},
        ]
        client.get.return_value = _status("26.7", "update")
        r = await FirmwareManager(client).ensure("upgraded", check_timeout=0)
        assert r.action == "upgraded"
        assert client.post.await_args_list[2].args[0] == "core/firmware/update"

    async def test_check_mode_never_fires(self, client: AsyncMock) -> None:
        client.post.side_effect = [{"status": "ok"}, {"status": "done", "log": ""}]
        client.get.return_value = _status("26.7", "update")
        r = await FirmwareManager(client).ensure(
            "updated", target="26.7.3", check_mode=True, check_timeout=0
        )
        assert r.changed is True and r.after["product_version"] == "26.7.3"
        assert client.post.await_count == 2

    async def test_invalid_state(self, client: AsyncMock) -> None:
        with pytest.raises(ValueError):
            await FirmwareManager(client).ensure("latest")


@pytest.mark.asyncio
class TestWaitForVersion:
    async def test_times_out(self, client: AsyncMock) -> None:
        client.get.return_value = _status("26.7", "none")
        fw = FirmwareManager(client)
        with pytest.raises(OpnsenseTimeoutError):
            await fw.wait_for_version("26.7.3", timeout=0, interval=0)

    async def test_wait_polls_with_one_attempt_per_round(self, client: AsyncMock) -> None:
        # A poll must send exactly one request per round: max_retries=0 sends none
        # (client counts attempts) and the wait failed "after 0 attempts" on a live update.
        client.get.return_value = _status("26.7.3", "none")
        fw = FirmwareManager(client)
        assert await fw.wait_for_version("26.7.3", timeout=0, interval=0) == "26.7.3"
        args, kwargs = client.get.call_args
        assert kwargs.get("max_retries") == 1
        # 2026-09-21 drill: status reports no version until a check ran → the wait never ended
        assert args[0] == "core/firmware/info"


@pytest.mark.asyncio
class TestFireTolerance:
    async def test_update_request_cut_mid_stream_still_waits_for_the_version(
        self, client: AsyncMock
    ) -> None:
        # 2026-09-21 drill: the appliance restarted its web server as the update began and the
        # reply was cut ("malformed chunk footer"); the request had gone out.
        client.post.side_effect = [
            {"status": "ok"},  # check job
            {"status": "done", "log": ""},  # upgradestatus
            OpnsenseConnectionError("cut", endpoint="core/firmware/update"),  # update
        ]
        client.get.side_effect = [
            _status("26.7", "update"),  # resolved status after the check
            _status("26.7.4", "none"),  # info after the reboot
        ]
        fw = FirmwareManager(client)
        result = await fw.ensure("updated", target="26.7.4", wait_timeout=0, wait_interval=0)
        assert result.changed is True
        assert result.after["product_version"] == "26.7.4"
