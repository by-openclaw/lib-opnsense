# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense NetFlow / Insight settings manager — singleton config (getconfig/setconfig).

API domain: /api/diagnostics/netflow
Payload key: netflow
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  diagnostics/netflow/getconfig
    set   POST diagnostics/netflow/setconfig  ({"netflow": {...}})
    apply POST diagnostics/netflow/reconfigure

The document is nested::

    {"netflow": {"capture": {"interfaces": ..., "egress_only": ..., "version": ...,
                             "targets": ...},
                 "collect": {"enable": "1"},
                 "activeTimeout": "1800", "inactiveTimeout": "15"}}

``capture.interfaces`` / ``capture.egress_only`` / ``capture.targets`` are multi-selects —
pass a list or a CSV string; order does not matter. A partial document is merged by the
API: sub-fields that are not sent keep their value.

``setconfig`` answers ``{"result": "saved"}`` and a validation failure names the field
(``netflow.capture.interfaces: Option [x] not in list.``) — verified on OPNsense 26.7.5.
Until then the capture configuration could only be written by the seed (config.xml); with
this manager it is declared like every other setting. Service state (``status`` /
``reconfigure`` alone) stays with :class:`NetflowServiceManager`.
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_CAPTURE_MULTI_SELECT_FIELDS: tuple[str, ...] = (
    "interfaces",
    "egress_only",
    "targets",
)


class NetflowSettingsManager(BaseSingletonManager):
    """Manage the NetFlow capture and local collection settings.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`; only the keys you pass are diffed.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = NetflowSettingsManager(client)
            await mgr.ensure("present", {
                "capture": {"interfaces": ["lan", "opt1"], "egress_only": ["wan"],
                            "version": "v9", "targets": ["127.0.0.1:2056"]},
                "collect": {"enable": "1"},
            })

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings.
        after:    Settings after the set (or projected in ``check_mode``).
    """

    _endpoint = "diagnostics/netflow"
    _payload_key = "netflow"
    _get_action = "getconfig"
    _set_action = "setconfig"
    _apply_endpoint = "diagnostics/netflow/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "capture": {
            "type": "dict",
            "fields": {
                # Multi-selects (CSV after normalisation); the options are the device's
                # interfaces, so the API validates the values.
                "interfaces": {"type": "str", "max_length": 1024},
                "egress_only": {"type": "str", "max_length": 1024},
                "version": {"type": "enum", "values": ["v5", "v9"]},
                "targets": {"type": "str", "max_length": 1024},
            },
        },
        "collect": {
            "type": "dict",
            "fields": {
                "enable": {"type": "bool_str"},
            },
        },
        "activeTimeout": {"type": "str", "max_length": 10},
        "inactiveTimeout": {"type": "str", "max_length": 10},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure the settings match ``params`` (capture multi-selects normalised to CSV).

        Args:
            state:      Must be ``'present'``.
            params:     Desired settings; the capture multi-select fields may be lists.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` describing what was (or would be) done.
        """
        normalised = dict(params)
        if isinstance(normalised.get("capture"), dict):
            capture = dict(normalised["capture"])
            for field in _CAPTURE_MULTI_SELECT_FIELDS:
                if field in capture:
                    capture[field] = normalize_multi_select(capture[field])
            normalised["capture"] = capture
        return await super().ensure(state, normalised, check_mode=check_mode)
