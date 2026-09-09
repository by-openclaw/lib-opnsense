# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Monit alert manager — CRUD + ensure() for Monit alert recipients.

API domain: /api/monit/settings
Payload key: alert
Match key:   recipient (email/notification target)
Entity suffix: Alert (searchAlert, getAlert, addAlert, setAlert, delAlert)

Endpoints:
    search  GET  monit/settings/searchAlert
    get     GET  monit/settings/getAlert/{uuid}
    create  POST monit/settings/addAlert
    update  POST monit/settings/setAlert/{uuid}
    delete  POST monit/settings/delAlert/{uuid}
    apply   POST monit/service/reconfigure

Notes:
    - ``events`` is an OPNsense multi-select: a GET returns a dict of selectable
      enum slots, but a POST expects a comma-separated string of slot keys
      (e.g. ``"action,connection,timeout"``). Pass a list/tuple/set or a CSV
      string; it is normalised on ``ensure``.
    - ``recipient`` is the human-meaningful identity; OPNsense does not enforce
      uniqueness, so duplicates would raise ``AmbiguousMatchError`` from the
      identity resolver.

Reference: https://docs.opnsense.org/manual/monit.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

# Valid event slot keys (multi-select) — from the monit-alert schema.
_EVENT_VALUES = [
    "action",
    "checksum",
    "bytein",
    "byteout",
    "connection",
    "content",
    "data",
    "exec",
    "fsflags",
    "gid",
    "icmp",
    "instance",
    "invalid",
    "link",
    "nonexist",
    "packetin",
    "packetout",
    "permission",
    "pid",
    "ppid",
    "resource",
    "saturation",
    "size",
    "speed",
    "status",
    "timeout",
    "timestamp",
    "uid",
    "uptime",
]


def _normalize_events(value: Any) -> str:
    """Normalise the ``events`` multi-select to a comma-separated string.

    Accepts a string passthrough or a list/tuple/set of event slot keys.
    """
    if isinstance(value, list | tuple | set):
        return ",".join(str(x) for x in value)
    return str(value) if value is not None else ""


class MonitAlertManager(BaseManager):
    """Manage OPNsense Monit alert recipients via /api/monit/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. Each alert
    defines a recipient and the set of Monit events that trigger a
    notification. The ``events`` field is a multi-select normalised to CSV.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = MonitAlertManager(client)
            await mgr.ensure("present", {
                "enabled": "1",
                "recipient": "noc@example.com",
                "events": ["connection", "timeout", "status"],
            })

    Input (ensure present):
        recipient:    Notification target (email), max 255 (required)
        enabled:      Enable this alert (bool_str, optional)
        noton:        Invert event match — alert on all BUT listed events
                      (bool_str, optional)
        events:       Event slots — CSV string or list of:
                      action, checksum, bytein, byteout, connection, content,
                      data, exec, fsflags, gid, icmp, instance, invalid, link,
                      nonexist, packetin, packetout, permission, pid, ppid,
                      resource, saturation, size, speed, status, timeout,
                      timestamp, uid, uptime (optional)
        format:       Custom mail format override (optional)
        reminder:     Reminder interval in cycles (optional)
        description:  Free-text description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "monit/settings"
    _payload_key = "alert"
    _entity_suffix = "Alert"
    _apply_endpoint = "monit/service/reconfigure"
    _match_key = "recipient"

    REDACT_FIELDS: set[str] = {"recipient"}

    _validators = {
        "recipient": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "noton": {"type": "bool_str"},
        "events": {"type": "str"},
        "format": {"type": "str"},
        "reminder": {"type": "str", "max_length": 10},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Monit alert manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
        uuid: str | None = None,
        dedupe: bool = False,
    ) -> Any:
        """Normalise the ``events`` multi-select then delegate to base ``ensure``.

        ``events`` accepts a string or a list/tuple/set on input; the API
        requires a comma-separated string on ``add``/``set``. We coerce here
        so callers don't have to remember.
        """
        if state == "present" and "events" in params:
            normalized = dict(params)
            normalized["events"] = _normalize_events(normalized["events"])
            params = normalized
        return await super().ensure(state, params, check_mode=check_mode, uuid=uuid, dedupe=dedupe)
