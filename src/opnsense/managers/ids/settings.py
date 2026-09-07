# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Intrusion Detection (Suricata) general settings manager — singleton config (get/set).

API domain: /api/ids/settings
Payload key: ids / section: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  ids/settings/get
    set   POST ids/settings/set
    apply POST ids/service/reconfigure

``mode``: ``pcap`` = IDS (alert only), ``netmap``/``divert`` = inline IPS.
``interfaces``/``homenet``/``eveLog`` are multi-selects (list or CSV; ``homenet`` is
free-form networks). ``syslog_eve``
forwards EVE alerts to syslog (the Loki path). Rulesets are toggled through
:class:`~opnsense.managers.ids.ruleset.IdsRulesetManager`.

Schema discovered from ``GET /api/ids/settings/get`` on OPNsense 26.7.3.
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = (
    "interfaces",
    "homenet",
    "eveLog",
)


class IdsSettingsManager(BaseSingletonManager):
    """OPNsense Intrusion Detection (Suricata) general settings manager.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IdsSettingsManager(client)
            await mgr.ensure("present", {"enabled": "1", "mode": "pcap", "interfaces": ["opt12"],
                                     "homenet": ["10.1.0.0/16", "fd01::/32"], "syslog_eve": "1"})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
    """

    _endpoint = "ids/settings"
    _payload_key = "ids"
    _section = "general"
    _apply_endpoint = "ids/service/reconfigure"
    _apply_timeout = 120

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "promisc": {"type": "bool_str"},
        "syslog": {"type": "bool_str"},
        "syslog_eve": {"type": "bool_str"},
        "LogPayload": {"type": "bool_str"},
        "divert_listeners": {"type": "bool_str"},
        # String / numeric-as-string fields
        "AlertSaveLogs": {"type": "str", "max_length": 10},
        "defaultPacketSize": {"type": "str", "max_length": 10},
        # Multi-select (CSV after normalisation)
        "interfaces": {"type": "str", "max_length": 4096},
        "homenet": {"type": "str", "max_length": 4096},
        "eveLog": {"type": "str", "max_length": 4096},
        "mode": {"type": "enum", "values": ["pcap", "netmap", "divert"]},
        "AlertLogrotate": {"type": "enum", "values": ["D0", "W0D23"]},
        "MPMAlgo": {"type": "enum", "values": ["", "ac", "ac-ks", "hs"]},
        "verbosity": {"type": "enum", "values": ["", "v", "vv", "vvv", "vvvv"]},
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
        """Ensure the settings match ``params`` (multi-select lists normalised to CSV)."""
        normalised = dict(params)
        for field in _MULTI_SELECT_FIELDS:
            if field in normalised:
                normalised[field] = normalize_multi_select(normalised[field])
        return await super().ensure(state, normalised, check_mode=check_mode)
