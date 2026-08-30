# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME service controller — start/stop/restart/reconfigure + configtest.

API domain: /api/acmeclient/service  (os-acme-client plugin)
Pattern:    BaseServiceManager — idempotent state transitions.

After CRUD on accounts/validations/certificates/actions (which store config
immediately), call :meth:`reconfigure` once to regenerate the acme.sh configs
and the auto-renewal cron. :meth:`configtest` validates the generated config.

Endpoints:
    status       GET  acmeclient/service/status
    start        POST acmeclient/service/start
    stop         POST acmeclient/service/stop
    restart      POST acmeclient/service/restart
    reconfigure  POST acmeclient/service/reconfigure
    configtest   GET  acmeclient/service/configtest

Reference: https://github.com/opnsense/plugins/tree/master/security/acme-client
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager

logger = logging.getLogger(__name__)


class AcmeServiceManager(BaseServiceManager):
    """Control the os-acme-client service via /api/acmeclient/service.

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`, and adds :meth:`configtest`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AcmeServiceManager(client)
            await mgr.ensure("reconfigured")     # regenerate acme.sh cfg + cron
            ok = await mgr.configtest()          # validate generated config

    Input (ensure):
        state: 'running' | 'stopped' | 'reconfigured'.

    Output (EnsureResult):
        action: 'started' | 'stopped' | 'restarted' | 'reconfigured' | 'noop'.
    """

    _endpoint = "acmeclient/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ACME service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def configtest(self) -> str:
        """Validate the generated ACME configuration (``configtest`` verb).

        Returns:
            The ``result`` string from the API (e.g. 'OK' on success).
        """
        try:
            body = await self._client.get(f"{self._endpoint}/configtest")
        except Exception as exc:
            logger.error(
                "configtest failed %s: %s",
                self._endpoint,
                exc,
                extra={
                    "action": "configtest_failed",
                    "endpoint": self._endpoint,
                    "error": str(exc),
                },
            )
            raise
        return str(body.get("result", ""))
