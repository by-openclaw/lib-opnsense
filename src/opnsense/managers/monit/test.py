# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Monit test manager — CRUD + ensure() for Monit test definitions.

API domain: /api/monit/settings
Payload key: test
Match key:   name (unique test name)
Entity suffix: Test (searchTest, getTest, addTest, setTest, delTest)

A Monit "test" is a reusable check (e.g. CPU usage, ping, file checksum) that
services reference by UUID. CRUD here; service-to-test wiring lives on the
service ``tests`` field.

Endpoints:
    search  GET  monit/settings/searchTest
    get     GET  monit/settings/getTest/{uuid}
    create  POST monit/settings/addTest
    update  POST monit/settings/setTest/{uuid}
    delete  POST monit/settings/delTest/{uuid}
    apply   POST monit/service/reconfigure

Reference: https://docs.opnsense.org/manual/monit.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class MonitTestManager(BaseManager):
    """Manage OPNsense Monit test definitions via /api/monit/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. Tests are
    referenced by UUID from services. The ``type`` enum values are the
    OPNsense slot keys (CamelCase), not their display labels.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = MonitTestManager(client)
            await mgr.ensure("present", {
                "name": "CPUUsage90",
                "type": "SystemResource",
                "condition": "cpu usage is greater than 90%",
                "action": "alert",
            })

    Input (ensure present):
        name:       Test name, max 255 (required)
        type:       Test type — Existence, SystemResource, ProcessResource,
                    ProcessDiskIO, FileChecksum, Timestamp, FileSize,
                    FileContent, FilesystemMountFlags, SpaceUsage, InodeUsage,
                    DiskIO, Permisssion, UID, GID, PID, PPID, Uptime,
                    ProgramStatus, NetworkInterface, NetworkPing, Connection,
                    Custom (optional)
        condition:  Monit condition expression (optional)
        action:     Action on match — alert, restart, start, stop, exec,
                    unmonitor (optional)
        path:       Path/argument for Program/Custom tests (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "monit/settings"
    _payload_key = "test"
    _entity_suffix = "Test"
    _apply_endpoint = "monit/service/reconfigure"
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "type": {
            "type": "enum",
            "values": [
                "Existence",
                "SystemResource",
                "ProcessResource",
                "ProcessDiskIO",
                "FileChecksum",
                "Timestamp",
                "FileSize",
                "FileContent",
                "FilesystemMountFlags",
                "SpaceUsage",
                "InodeUsage",
                "DiskIO",
                # Note: OPNsense schema spells this with a triple 's'.
                "Permisssion",
                "UID",
                "GID",
                "PID",
                "PPID",
                "Uptime",
                "ProgramStatus",
                "NetworkInterface",
                "NetworkPing",
                "Connection",
                "Custom",
            ],
        },
        "condition": {"type": "str"},
        "action": {
            "type": "enum",
            "values": ["alert", "restart", "start", "stop", "exec", "unmonitor"],
        },
        "path": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Monit test manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
