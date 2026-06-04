# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Monit global settings manager — singleton config (get/set).

API domain: /api/monit/settings
Payload key: monit
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

The Monit ``settings/get`` document wraps the general daemon config under the
``general`` object (alongside ``alert``/``service``/``test`` collections, which
have their own managers). This manager only manages the ``general`` block; on
``set`` the params are sent as ``{"monit": {"general": {...}}}``.

Endpoints:
    get   GET  monit/settings/get
    set   POST monit/settings/set
    apply POST monit/service/reconfigure

Redact fields: password, httpdPassword, username, httpdUsername,
               mmonitUrl (may embed credentials).

Reference: https://docs.opnsense.org/manual/monit.html
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.diff import DiffEngine
from opnsense.core.logging_helpers import ManagerLogBuilder
from opnsense.core.redaction import Redactor
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)

_diff_engine = DiffEngine()
_redactor = Redactor()


class MonitSettingsManager(BaseSingletonManager):
    """Manage the OPNsense Monit global daemon config via /api/monit/settings.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`. The collections ``alert``, ``service`` and
    ``test`` are managed by their dedicated ``Monit*Manager`` classes — not by
    this one. Params are nested under the ``general`` object so the diff/set
    operate on the same shape the API returns.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = MonitSettingsManager(client)
            await mgr.ensure("present", {
                "enabled": "1",
                "interval": "120",
                "mailserver": "127.0.0.1",
                "port": "25",
            })

    Input (ensure present) — all optional; only passed keys are diffed:
        enabled:                    Enable Monit daemon (bool_str)
        interval:                   Poll interval in seconds (str)
        startdelay:                 Startup delay in seconds (str)
        mailserver:                 SMTP mail server host (str)
        port:                       SMTP port (str)
        username:                   SMTP auth username (str, redacted)
        password:                   SMTP auth password (str, redacted)
        ssl:                        Enable SSL for SMTP (bool_str)
        sslversion:                 SSL/TLS version — AUTO, TLSV1, TLSV11,
                                    TLSV12, TLSV13 (enum)
        sslverify:                  Verify SSL server certificate (bool_str)
        logfile:                    Monit log file path (str)
        statefile:                  Monit state file path (str)
        eventqueuePath:             Event queue directory (str)
        eventqueueSlots:            Event queue slot count (str)
        httpdEnabled:               Enable the Monit HTTP status server (bool_str)
        httpdUsername:              HTTP server username (str, redacted)
        httpdPassword:              HTTP server password (str, redacted)
        httpdPort:                  HTTP server port (str)
        httpdAllow:                 Allowed host/network for HTTP server (str)
        mmonitUrl:                  M/Monit collector URL (str, redacted)
        mmonitTimeout:              M/Monit connection timeout in seconds (str)
        mmonitRegisterCredentials:  Register Monit credentials with M/Monit
                                    (bool_str)

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings (redacted).
        after:    Settings after the set (redacted).
    """

    _endpoint = "monit/settings"
    _payload_key = "monit"
    _apply_endpoint = "monit/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = {
        "password",
        "httpdPassword",
        "username",
        "httpdUsername",
        "mmonitUrl",
    }

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "ssl": {"type": "bool_str"},
        "sslverify": {"type": "bool_str"},
        "httpdEnabled": {"type": "bool_str"},
        "mmonitRegisterCredentials": {"type": "bool_str"},
        # Numeric-as-string fields
        "interval": {"type": "str", "max_length": 10},
        "startdelay": {"type": "str", "max_length": 10},
        "port": {"type": "str", "max_length": 5},
        "httpdPort": {"type": "str", "max_length": 5},
        "eventqueueSlots": {"type": "str", "max_length": 10},
        "mmonitTimeout": {"type": "str", "max_length": 10},
        # String fields
        "mailserver": {"type": "str", "max_length": 255},
        "username": {"type": "str", "max_length": 255},
        "password": {"type": "str", "max_length": 255},
        "logfile": {"type": "str", "max_length": 255},
        "statefile": {"type": "str", "max_length": 255},
        "eventqueuePath": {"type": "str", "max_length": 255},
        "httpdUsername": {"type": "str", "max_length": 255},
        "httpdPassword": {"type": "str", "max_length": 255},
        "httpdAllow": {"type": "str", "max_length": 255},
        "mmonitUrl": {"type": "str", "max_length": 255},
        # Single-select enum
        "sslversion": {
            "type": "enum",
            "values": ["AUTO", "TLSV1", "TLSV11", "TLSV12", "TLSV13"],
        },
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Monit settings manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def get(self) -> dict[str, Any]:
        """Fetch the current Monit ``general`` settings block.

        The ``settings/get`` payload nests the daemon config under
        ``general``; we unwrap it so callers diff a flat dict.

        Returns:
            The ``general`` settings dict (empty dict if absent).
        """
        body = await super().get()
        general = body.get("general", {})
        return general if isinstance(general, dict) else {}

    async def set(
        self,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Update the Monit ``general`` settings (fetch → diff → POST if drifted).

        Mirrors :meth:`BaseSingletonManager.set` but keeps ``before`` and
        ``params`` in the same flat ``general`` shape for diffing, while
        nesting under ``general`` on the POST body that the API requires:
        ``{"monit": {"general": {...}}}``.

        Args:
            params:     Desired ``general`` settings (flat dict).
            check_mode: If True, return what would happen without making changes.

        Returns:
            ``EnsureResult`` with ``action='updated'`` or ``'noop'``.
        """
        log = ManagerLogBuilder()
        before = await self.get()
        diff = _diff_engine.compute_diff(before, params)

        redacted_before = _redactor.redact_dict(before, redact_fields=self.REDACT_FIELDS)

        if diff is None:
            logger.debug(
                "noop %s — settings match",
                self._endpoint,
                extra=log.build_extra("noop", {}, before=redacted_before, changed=False),
            )
            return EnsureResult(
                changed=False,
                action="noop",
                before=redacted_before,
                after=redacted_before,
            )

        projected_after = {**before, **params}
        redacted_after = _redactor.redact_dict(projected_after, redact_fields=self.REDACT_FIELDS)

        if check_mode:
            logger.info(
                "set check_mode=True %s",
                self._endpoint,
                extra=log.build_extra(
                    "updated",
                    {},
                    before=redacted_before,
                    after=redacted_after,
                    changed=True,
                    check_mode=True,
                ),
            )
            return EnsureResult(
                changed=True,
                action="updated",
                before=redacted_before,
                after=redacted_after,
            )

        try:
            await self._client.post(
                f"{self._endpoint}/set",
                {self._payload_key: {"general": params}},
            )
            await self._apply()
        except Exception as exc:
            logger.error(
                "set failed %s: %s",
                self._endpoint,
                exc,
                extra=log.build_extra("update_failed", {}, before=redacted_before, error=str(exc)),
            )
            raise

        actual_after = await self.get()
        redacted_actual = _redactor.redact_dict(actual_after, redact_fields=self.REDACT_FIELDS)

        logger.info(
            "updated %s",
            self._endpoint,
            extra=log.build_extra(
                "updated",
                {},
                before=redacted_before,
                after=redacted_actual,
                changed=True,
            ),
        )
        return EnsureResult(
            changed=True,
            action="updated",
            before=redacted_before,
            after=redacted_actual,
        )
