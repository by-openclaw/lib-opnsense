# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for PluginManager.ensure() — idempotent install/remove with the job-log verdict.

The firmware backend answers ``status=done`` for a REFUSED job too; the verdict lives in
the job log. These tests cover noop, install, remove, check_mode, refusal, unknown package,
state-unchanged-after-done and job timeout (``interval=0`` keeps them instant).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseServerError, OpnsenseTimeoutError
from opnsense.managers.services.plugin import PluginManager


def _info(installed: dict[str, str]) -> dict:
    return {"package": [{"name": n, "installed": v} for n, v in installed.items()]}


@pytest.fixture
def client() -> AsyncMock:
    c = AsyncMock(spec=OpnsenseClient)
    c._base_url = "https://opnsense.example.com"
    return c


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_already_installed(self, client: AsyncMock) -> None:
        client.get.return_value = _info({"os-chrony": "1"})
        r = await PluginManager(client).ensure("os-chrony", "present", interval=0)
        assert r.changed is False and r.action == "noop" and r.before == {"installed": True}
        client.post.assert_not_awaited()

    async def test_install_waits_and_verifies(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            _info({"os-chrony": "0"}),  # before
            {"status": "ready"},  # firmware subsystem idle
            {"status": "running", "log": ""},  # upgradestatus poll 1
            {
                "status": "done",
                "log": (
                    "***GOT REQUEST TO INSTALL***\nNew packages to be INSTALLED:\n"
                    "\tos-chrony\n***DONE***"
                ),
            },
            _info({"os-chrony": "1"}),  # after
        ]
        client.post.return_value = {"status": "ok", "msg_uuid": "x"}
        r = await PluginManager(client).ensure("os-chrony", "present", interval=0)
        assert r.changed is True and r.action == "installed" and r.after == {"installed": True}
        client.post.assert_awaited_once_with("core/firmware/install/os-chrony", data={})

    async def test_remove(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            _info({"os-lldpd": "1"}),
            {"status": "ready"},
            {"status": "done", "log": "Deinstallation of os-lldpd ***DONE***"},
            _info({"os-lldpd": "0"}),
        ]
        client.post.return_value = {"status": "ok"}
        r = await PluginManager(client).ensure("os-lldpd", "absent", interval=0)
        assert r.action == "removed" and r.after == {"installed": False}
        client.post.assert_awaited_once_with("core/firmware/remove/os-lldpd", data={})

    async def test_check_mode_does_not_fire(self, client: AsyncMock) -> None:
        client.get.return_value = _info({"os-chrony": "0"})
        r = await PluginManager(client).ensure("os-chrony", "present", check_mode=True)
        assert r.changed is True and r.action == "installed" and r.after == {"installed": True}
        client.post.assert_not_awaited()

    async def test_refused_out_of_date_raises(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            _info({"os-chrony": "0"}),
            {"status": "ready"},
            {
                "status": "done",
                "log": (
                    "***GOT REQUEST TO INSTALL***\nInstallation out of date. "
                    "The update to opnsense-26.7.3_11 is required.\n***DONE***"
                ),
            },
        ]
        client.post.return_value = {"status": "ok"}
        with pytest.raises(OpnsenseServerError, match="out of date"):
            await PluginManager(client).ensure("os-chrony", "present", interval=0)

    async def test_unknown_package_raises(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            _info({}),
            {"status": "ready"},
            {
                "status": "done",
                "log": (
                    "No packages available to install matching 'os-nope' "
                    "have been found in the repositories\n***DONE***"
                ),
            },
        ]
        client.post.return_value = {"status": "ok"}
        with pytest.raises(OpnsenseServerError, match="unknown package"):
            await PluginManager(client).ensure("os-nope", "present", interval=0)

    async def test_done_but_state_unchanged_raises(self, client: AsyncMock) -> None:
        client.get.side_effect = [
            _info({"os-chrony": "0"}),
            {"status": "ready"},
            {"status": "done", "log": "***DONE***"},
            _info({"os-chrony": "0"}),
        ]
        client.post.return_value = {"status": "ok"}
        with pytest.raises(OpnsenseServerError, match="still absent"):
            await PluginManager(client).ensure(
                "os-chrony", "present", interval=0, verify_retries=0, verify_interval=0
            )

    async def test_job_timeout_raises(self, client: AsyncMock) -> None:
        client.get.side_effect = [_info({"os-chrony": "0"}), {"status": "ready"}] + [
            {"status": "running", "log": ""}
        ] * 5
        client.post.return_value = {"status": "ok"}
        with pytest.raises(OpnsenseTimeoutError):
            await PluginManager(client).ensure("os-chrony", "present", timeout=0, interval=0)

    async def test_invalid_state(self, client: AsyncMock) -> None:
        with pytest.raises(ValueError):
            await PluginManager(client).ensure("os-chrony", "latest")

    async def test_waits_for_the_firmware_subsystem_before_firing(self, client: AsyncMock) -> None:
        # 2026-09-21 rebuild: the appliance re-installs its configured plugins itself right
        # after the update reboot; an install fired meanwhile ended in job 'error'.
        client.get.side_effect = [
            _info({"os-chrony": "0"}),
            {"status": "busy"},
            {"status": "busy"},
            {"status": "ready"},
            {"status": "done", "log": "***DONE***"},
            _info({"os-chrony": "1"}),
        ]
        client.post.return_value = {"status": "ok"}
        r = await PluginManager(client).ensure("os-chrony", "present", interval=0)
        assert r.action == "installed"
        assert [c.args[0] for c in client.get.await_args_list[1:4]] == ["core/firmware/running"] * 3

    async def test_never_idle_raises_without_firing(self, client: AsyncMock) -> None:
        client.get.side_effect = [_info({"os-chrony": "0"})] + [{"status": "busy"}] * 5
        with pytest.raises(OpnsenseTimeoutError, match="still busy"):
            await PluginManager(client).ensure("os-chrony", "present", timeout=0, interval=0)
        client.post.assert_not_awaited()

    async def test_error_with_an_empty_log_means_the_job_is_starting(
        self, client: AsyncMock
    ) -> None:
        # 2026-09-21 rebuild: right after the install request the progress log is still empty
        # and the appliance reports status 'error' (FirmwareController::upgradestatusAction:
        # empty output → 'error'); the job then runs to ***DONE***.
        client.get.side_effect = [
            _info({"os-acme-client": "0"}),
            {"status": "ready"},
            {"status": "error", "log": ""},
            {"status": "error", "log": ""},
            {"status": "running", "log": "***GOT REQUEST TO INSTALL***"},
            {"status": "done", "log": "***GOT REQUEST TO INSTALL***\nos-acme-client\n***DONE***"},
            _info({"os-acme-client": "1"}),
        ]
        client.post.return_value = {"status": "ok"}
        r = await PluginManager(client).ensure("os-acme-client", "present", interval=0)
        assert r.changed is True and r.action == "installed"
        client.post.assert_awaited_once_with("core/firmware/install/os-acme-client", data={})

    async def test_error_that_never_clears_times_out(self, client: AsyncMock) -> None:
        client.get.side_effect = [_info({"os-chrony": "0"}), {"status": "ready"}] + [
            {"status": "error", "log": ""}
        ] * 5
        client.post.return_value = {"status": "ok"}
        with pytest.raises(OpnsenseTimeoutError, match="still 'error'"):
            await PluginManager(client).ensure("os-chrony", "present", timeout=0, interval=0)


@pytest.mark.asyncio
async def test_done_with_lagging_cache_is_verified_on_reread(client: AsyncMock) -> None:
    # The job says done ("Nothing to do": the appliance installed it itself after a firmware
    # update) while core/firmware/info still serves the old cache; a later re-read confirms it.
    client.get.side_effect = [
        _info({"os-ddclient": "0"}),  # pre-check: absent
        {"status": "ready"},  # firmware subsystem idle
        {"status": "done", "log": "Checking integrity... done\nNothing to do.\n***DONE***"},
        _info({"os-ddclient": "0"}),  # first re-read: cache lags
        _info({"os-ddclient": "1"}),  # second re-read: present
    ]
    client.post.return_value = {"status": "ok"}
    result = await PluginManager(client).ensure(
        "os-ddclient", "present", interval=0, verify_retries=3, verify_interval=0
    )
    assert result.changed is True
    assert result.after == {"installed": True}
