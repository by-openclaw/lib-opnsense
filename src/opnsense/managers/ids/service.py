# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IDS (Suricata) service controller — start/stop/restart/reconfigure + rule updates.

API domain: /api/ids/service
Pattern:    BaseServiceManager + ``update_rules()``.

Endpoints:
    status       GET  ids/service/status
    start/stop/restart/reconfigure  POST ids/service/<verb>
    updateRules  POST ids/service/updateRules   (download enabled rulesets; long-running)
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager

logger = logging.getLogger(__name__)


class IdsServiceManager(BaseServiceManager):
    """Control Suricata and trigger rule downloads.

    Usage::

        async with OpnsenseClient(...) as client:
            svc = IdsServiceManager(client)
            await svc.update_rules()           # fetch the enabled rulesets
            await svc.ensure("running")
    """

    _endpoint = "ids/service"
    _apply_timeout = 120

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IDS service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def update_rules(self, timeout: int = 600) -> dict[str, Any]:
        """Download/refresh the enabled rulesets (``updateRules``); returns the API response."""
        try:
            result = await self._client.post(
                f"{self._endpoint}/updateRules", data={}, timeout=timeout
            )
        except Exception as exc:
            logger.error(
                "ids updateRules failed: %s",
                exc,
                extra={"action": "update_rules_failed", "error": str(exc)},
            )
            raise
        logger.info(
            "ids rules updated", extra={"action": "update_rules", "result": str(result)[:120]}
        )
        return result
