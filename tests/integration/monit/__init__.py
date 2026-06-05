# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests for the Monit managers (live OPNsense device).

Shared health gate
------------------
Per the platform rule "integration test = ALWAYS read the service status/log to
verify no error": a Monit API call returning ``{"result":"saved"}`` only proves
the API accepted the config, NOT that the monit daemon survived the
``reconfigure`` that regenerates ``/usr/local/etc/monitrc`` and restarts it. A
bad payload (e.g. a multi-word ``exec`` path) makes monit fail to parse its
control file and crash-loop — invisible at the API layer.

``assert_monit_healthy`` reads the daemon's own status after an apply and fails
loudly if monit is not running, so a test object can never leave the daemon
broken without the test catching it.
"""

from __future__ import annotations

import asyncio
from typing import Any

from opnsense.client import OpnsenseClient

# A single-token, always-present, no-op command. Monit's monitrc template emits
# an ``exec`` path verbatim and unquoted, so a multi-word command breaks parsing.
# Integration test objects MUST use this safe single-token exec — never a real
# multi-arg command (those belong in a seed-owned wrapper script).
SAFE_EXEC_PATH = "/usr/bin/true"


async def assert_monit_healthy(
    client: OpnsenseClient,
    *,
    attempts: int = 8,
    delay_s: float = 3.0,
) -> None:
    """Assert the monit daemon comes back healthy after a reconfigure.

    ``monit/service/reconfigure`` restarts the daemon, so for ~1-2s right after
    the call ``monit/service/status`` legitimately reports ``stopped`` while it
    comes back up. This polls until monit is stably ``running`` again:

    * ``monit/service/status`` -> ``{"status": "running"}``
    * ``monit/status/get``     -> ``{"result": "ok", "status": {"server": {...}}}``

    The distinction from a crash-loop (e.g. a monitrc parse error from a bad
    multi-word ``exec``) is that a crash-loop never settles into a running
    state with a live server block — so it exhausts the attempts and fails.

    Args:
        client:   Live OpnsenseClient.
        attempts: Max status polls before giving up (default 8 -> ~24s).
        delay_s:  Seconds between polls.

    Raises:
        AssertionError: if monit never returns to a stable running/ok state.
    """
    last: str | None = None
    for _ in range(attempts):
        svc: dict[str, Any] = await client.get("monit/service/status")
        last = str(svc.get("status"))
        if last == "running":
            status: dict[str, Any] = await client.get("monit/status/get")
            server = (status.get("status") or {}).get("server") or {}
            if status.get("result") == "ok" and server.get("id"):
                return  # daemon back up with a live server block — healthy
        await asyncio.sleep(delay_s)

    raise AssertionError(
        f"monit did not return to a stable running state after reconfigure "
        f"(last service.status={last!r}); likely a monitrc parse error — "
        "check /var/log/monit on the device"
    )
