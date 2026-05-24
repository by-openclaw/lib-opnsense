# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP option entry manager.

API domain: /api/dnsmasq/settings
Payload key: option
Match keys:  interface + option + option6 (v4 xor v6 per entry)
Entity suffix: Option

The server requires exactly one of ``option`` (DHCPv4) or ``option6`` (DHCPv6).
The unused field stays empty, so the three-field composite still distinguishes
entries uniquely.

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DnsmasqOptionManager(BaseManager):
    """Manage Dnsmasq DHCP options (v4 or v6) via /api/dnsmasq/settings.

    Input (ensure present):
        type:        ``'set'`` | ``'match'`` (default ``'set'``).
        option:      DHCPv4 option number (e.g. ``'3'`` = routers).
        option6:     DHCPv6 option number (alternative to ``option``).
        interface:   Optional interface scope.
        tag:         Optional tag (CSV).
        set_tag:     Optional set-tag.
        value:       Option value.
        force:       ``'0'`` | ``'1'`` — always send.
        description: Free-text description.

    At least one of ``option`` / ``option6`` must be set (server validates).

    Output (EnsureResult): standard CRUD result.
    """

    _endpoint = "dnsmasq/settings"
    _payload_key = "option"
    _entity_suffix = "Option"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["interface", "option", "option6"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "type": {"type": "enum", "values": ["set", "match"]},
        "option": {"type": "str", "max_length": 8},
        "option6": {"type": "str", "max_length": 8},
        "interface": {"type": "str", "max_length": 32},
        "tag": {"type": "str", "max_length": 255},
        "set_tag": {"type": "str", "max_length": 64},
        "value": {"type": "str", "max_length": 1024},
        "force": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 1024},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq option manager."""
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List option entries (drops ``search_phrase``).

        Same display-value filter footgun as :class:`RadvdEntryManager`.
        """
        return await self._client.search(self._endpoints.search(), search_phrase="")
