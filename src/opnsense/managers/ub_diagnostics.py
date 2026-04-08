# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS diagnostics — read-only stats and DNSBL status.

NOT a BaseManager — these are read-only endpoints with no CRUD lifecycle.

Endpoints:
    stats       GET unbound/diagnostics/stats
    dnsbl list  POST unbound/settings/searchDnsbl
    dnsbl get   GET unbound/settings/getDnsbl

DNSBL LIMITATION: OPNsense 26.1.5 does not expose addDnsbl, setDnsbl,
or delDnsbl endpoints. DNSBL configuration is read-only via API.
Use WebGUI for DNSBL configuration until API support is added.
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient

logger = logging.getLogger(__name__)


class UbDiagnosticsManager:
    """Read-only Unbound DNS diagnostics — stats and DNSBL status.

    NOT a BaseManager subclass — no CRUD, no ensure().

    Usage::

        async with OpnsenseClient(...) as client:
            diag = UbDiagnosticsManager(client)
            stats = await diag.get_stats()
            dnsbl = await diag.get_dnsbl()
            blocklists = await diag.list_dnsbl()
    """

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the diagnostics manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    async def get_stats(self) -> dict[str, Any]:
        """Get Unbound resolver statistics.

        Returns:
            Dict with thread stats, cache info, query counts.
        """
        try:
            return await self._client.get("unbound/diagnostics/stats")
        except Exception as exc:
            logger.error(
                "get_stats failed: %s",
                exc,
                extra={"action": "get_stats_failed", "error": str(exc)},
            )
            raise

    async def get_dnsbl(self) -> dict[str, Any]:
        """Get DNSBL (blocklist) configuration.

        Returns the current blocklist settings. Read-only on 26.1.5 —
        addDnsbl/setDnsbl/delDnsbl return 404.

        Returns:
            Dict with blocklist configuration (enabled, type, lists, etc.).
        """
        try:
            body = await self._client.get("unbound/settings/getDnsbl")
            return body.get("blocklist", body)
        except Exception as exc:
            logger.error(
                "get_dnsbl failed: %s",
                exc,
                extra={"action": "get_dnsbl_failed", "error": str(exc)},
            )
            raise

    async def list_dnsbl(self) -> list[dict[str, Any]]:
        """List DNSBL entries via search endpoint.

        Returns:
            List of blocklist entry dicts.
        """
        try:
            return await self._client.search("unbound/settings/searchDnsbl")
        except Exception as exc:
            logger.error(
                "list_dnsbl failed: %s",
                exc,
                extra={"action": "list_dnsbl_failed", "error": str(exc)},
            )
            raise
