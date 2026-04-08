# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense cron job manager — CRUD + ensure().

API domain: /api/cron/settings
Payload key: job
Match key:   description (unique job description)
Entity suffix: Job (getJob, addJob, setJob, delJob)

Endpoints:
    search  POST cron/settings/searchJob  (standard search)
    get     GET  cron/settings/getJob/{uuid}
    create  POST cron/settings/addJob
    update  POST cron/settings/setJob/{uuid}
    delete  POST cron/settings/delJob/{uuid}
    apply   POST cron/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class CronJobManager(BaseManager):
    """Manage OPNsense cron jobs via /api/cron/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Cron jobs schedule recurring tasks on the OPNsense appliance.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = CronJobManager(client)
            result = await mgr.ensure("present", {
                "description": "Update bogons every night",
                "enabled": "1",
                "minutes": "0",
                "hours": "3",
                "days": "*",
                "months": "*",
                "weekdays": "*",
                "command": "filter update bogons",
                "who": "root",
                "parameters": "",
            })

    Input (ensure present):
        description:  Job description, max 255 (required)
        enabled:      Enable job ('0' or '1', optional, default='1')
        minutes:      Cron minutes (e.g. '0', '*/5')
        hours:        Cron hours (e.g. '0', '3')
        days:         Cron days (e.g. '*', '1,15')
        months:       Cron months (e.g. '*', '1-6')
        weekdays:     Cron weekdays (e.g. '*', '1-5')
        command:      Command to execute (OPNsense action name)
        who:          User to run as (default 'root')
        parameters:   Additional parameters for the command

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "cron/settings"
    _payload_key = "job"
    _entity_suffix = "Job"  # getJob, addJob, setJob, delJob
    _apply_endpoint = "cron/service/reconfigure"
    _apply_timeout = 15
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "minutes": {"type": "str"},
        "hours": {"type": "str"},
        "days": {"type": "str"},
        "months": {"type": "str"},
        "weekdays": {"type": "str"},
        "command": {"type": "str"},
        "who": {"type": "str"},
        "parameters": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the cron job manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List cron jobs — override because search uses plural (searchJobs)."""
        endpoint = f"{self._endpoint}/searchJobs"
        return await self._client.search(endpoint, search_phrase=search_phrase)
