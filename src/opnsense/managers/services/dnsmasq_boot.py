# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP boot/PXE entry manager.

API domain: /api/dnsmasq/settings
Payload key: boot
Match keys:  interface + filename
Entity suffix: Boot
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DnsmasqBootManager(BaseManager):
    """Manage Dnsmasq DHCP boot/PXE entries.

    Identity is the ``interface``+``filename`` composite — typical PXE setups
    serve a single boot file per interface.

    Input (ensure present):
        interface:   Interface slot (optional).
        tag:         Optional tag (CSV).
        filename:    PXE boot file (required).
        servername:  TFTP server name (optional).
        address:     TFTP server address (optional).
        description: Free-text description.

    Output (EnsureResult): standard CRUD result.
    """

    _endpoint = "dnsmasq/settings"
    _payload_key = "boot"
    _entity_suffix = "Boot"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["interface", "filename"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "interface": {"type": "str", "max_length": 32},
        "tag": {"type": "str", "max_length": 255},
        "filename": {"type": "str", "required": True, "max_length": 255},
        "servername": {"type": "str", "max_length": 255},
        "address": {"type": "str", "max_length": 128},
        "description": {"type": "str", "max_length": 1024},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq boot manager."""
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List boot entries (drops ``search_phrase``).

        OPNsense ``searchBoot`` filters against the ``%interface`` display
        value, not the slot id we match on. Same footgun as
        :class:`RadvdEntryManager`.
        """
        return await self._client.search(self._endpoints.search(), search_phrase="")
