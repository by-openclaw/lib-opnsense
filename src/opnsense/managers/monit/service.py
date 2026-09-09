# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Monit service manager — CRUD + ensure() for Monit monitored services.

API domain: /api/monit/settings
Payload key: service
Match key:   name (unique service name)
Entity suffix: Service (searchService, getService, addService, setService,
               delService)

A Monit "service" is a monitored entity (process, filesystem, host, system,
network, …) that binds a set of tests (by UUID) to a target. CRUD here.

Endpoints:
    search  GET  monit/settings/searchService
    get     GET  monit/settings/getService/{uuid}
    create  POST monit/settings/addService
    update  POST monit/settings/setService/{uuid}
    delete  POST monit/settings/delService/{uuid}
    apply   POST monit/service/reconfigure

Notes:
    - ``tests`` and ``depends`` are OPNsense multi-selects of UUIDs: a GET
      returns a dict of selectable slots, a POST expects a comma-separated
      string. Pass a list/tuple/set or CSV string; normalised on ``ensure``.
    - ``interface`` is a single-select whose valid values are device-specific
      (assigned interfaces); validated as a free string.

Reference: https://docs.opnsense.org/manual/monit.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


def _normalize_multi_select(value: Any) -> str:
    """Normalise a multi-select field to a comma-separated string.

    Accepts a string passthrough or a list/tuple/set of slot ids (UUIDs).
    """
    if isinstance(value, list | tuple | set):
        return ",".join(str(x) for x in value)
    return str(value) if value is not None else ""


class MonitServiceManager(BaseManager):
    """Manage OPNsense Monit monitored services via /api/monit/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. The ``tests``
    and ``depends`` multi-selects (UUID references) accept a list or CSV string
    and are normalised on input.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = MonitServiceManager(client)
            await mgr.ensure("present", {
                "enabled": "1",
                "name": "rootfs",
                "type": "filesystem",
                "path": "/",
                "tests": ["07e46b13-7368-4f50-8784-b01eab726713"],  # SpaceUsage
            })

    Input (ensure present):
        name:          Service name, max 255 (required)
        enabled:       Enable monitoring of this service (bool_str, optional)
        description:   Free-text description, max 255 (optional)
        type:          Service type — process, file, fifo, filesystem,
                       directory, host, system, custom, network (optional)
        pidfile:       PID file path (process type) (optional)
        match:         Process match string (optional)
        path:          Path/host/script depending on type (optional)
        timeout:       Service timeout in seconds (optional)
        starttimeout:  Start timeout in seconds (optional)
        address:       Address (host/network types) (optional)
        interface:     Bound interface (device-specific value) (optional)
        tests:         Test UUIDs — CSV string or list (optional)
        depends:       Dependency service UUIDs — CSV string or list (optional)
        start:         Start command (optional)
        stop:          Stop command (optional)
        polltime:      Cron-style poll schedule (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "monit/settings"
    _payload_key = "service"
    _entity_suffix = "Service"
    _apply_endpoint = "monit/service/reconfigure"
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 255},
        "type": {
            "type": "enum",
            "values": [
                "process",
                "file",
                "fifo",
                "filesystem",
                "directory",
                "host",
                "system",
                "custom",
                "network",
            ],
        },
        "pidfile": {"type": "str", "max_length": 255},
        "match": {"type": "str", "max_length": 255},
        "path": {"type": "str", "max_length": 255},
        "timeout": {"type": "str", "max_length": 10},
        "starttimeout": {"type": "str", "max_length": 10},
        "address": {"type": "str", "max_length": 255},
        "interface": {"type": "str", "max_length": 255},
        "tests": {"type": "str"},
        "depends": {"type": "str"},
        "start": {"type": "str", "max_length": 255},
        "stop": {"type": "str", "max_length": 255},
        "polltime": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Monit service manager.

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
        """Normalise multi-select fields then delegate to base ``ensure``.

        ``tests`` and ``depends`` accept a string or a list/tuple/set on
        input; the API requires a comma-separated string on ``add``/``set``.
        We coerce here so callers don't have to remember.
        """
        if state == "present":
            normalized = dict(params)
            for key in ("tests", "depends"):
                if key in normalized:
                    normalized[key] = _normalize_multi_select(normalized[key])
            params = normalized
        return await super().ensure(state, params, check_mode=check_mode, uuid=uuid, dedupe=dedupe)
