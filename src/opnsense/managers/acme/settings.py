# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME settings manager — singleton config (get/set).

API domain: /api/acmeclient/settings  (os-acme-client plugin)
Payload key: acmeclient
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

The ``settings/get`` document wraps the plugin config under the ``settings``
object (alongside ``accounts``/``certificates``/``validations``/``actions``
collections, which have their own managers). This manager only manages the
``settings`` block; on ``set`` the params are sent as
``{"acmeclient": {"settings": {...}}}`` (same nesting pattern as
:class:`MonitSettingsManager`'s ``general`` block).

Endpoints:
    get   GET  acmeclient/settings/get
    set   POST acmeclient/settings/set
    apply POST acmeclient/service/reconfigure

Reference: https://github.com/opnsense/plugins/tree/master/security/acme-client
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.diff import DiffEngine
from opnsense.core.logging_helpers import ManagerLogBuilder
from opnsense.core.redaction import Redactor
from opnsense.exceptions import OpnsenseServerError
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)

_diff_engine = DiffEngine()
_redactor = Redactor()


class AcmeSettingsManager(BaseSingletonManager):
    """Manage the os-acme-client global settings via /api/acmeclient/settings.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`. The ``accounts``/``certificates``/
    ``validations``/``actions`` collections are managed by their dedicated
    ``Acme*Manager`` classes — not by this one. Params are nested under the
    ``settings`` object so the diff/set operate on the same shape the API
    returns.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AcmeSettingsManager(client)
            await mgr.ensure("present", {"enabled": "1", "autoRenewal": "1"})

    Input (ensure present) — all optional; only passed keys are diffed:
        enabled:            Master enable ('1'/'0').
        autoRenewal:        Enable auto-renewal cron ('1'/'0').
        environment:        '' / 'prod' / 'stg'.
        challengePort:      HTTP-01 challenge port.
        TLSchallengePort:   TLS-ALPN-01 challenge port.
        restartTimeout:     Service-restart timeout (seconds).
        haproxyIntegration: Enable HAProxy integration ('1'/'0').
        logLevel:           'normal' / 'extended' / 'debug' / 'debug2' / 'debug3'.
        showIntro:          Show GUI intro panel ('1'/'0').

    Output (EnsureResult): updated/noop (singleton — never created/deleted);
    ``ensure(..., cron=True)`` adds ``cron_created`` (renewal cron job created/relinked).
    """

    _endpoint = "acmeclient/settings"
    _payload_key = "acmeclient"
    _apply_endpoint = "acmeclient/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "enabled": {"type": "bool_str"},
        "autoRenewal": {"type": "bool_str"},
        "haproxyIntegration": {"type": "bool_str"},
        "showIntro": {"type": "bool_str"},
        "environment": {"type": "enum", "values": ["", "prod", "stg"]},
        "logLevel": {
            "type": "enum",
            "values": ["normal", "extended", "debug", "debug2", "debug3"],
        },
        "challengePort": {"type": "str", "max_length": 5},
        "TLSchallengePort": {"type": "str", "max_length": 5},
        "restartTimeout": {"type": "str", "max_length": 10},
    }

    _cron_endpoint = "acmeclient/settings/fetchCronIntegration"

    async def ensure(  # type: ignore[override]
        self,
        state: str,
        params: dict[str, Any] | None = None,
        check_mode: bool = False,
        cron: bool = False,
    ) -> EnsureResult:
        """Converge the settings block and, with ``cron=True``, the auto-renewal cron job.

        The plugin creates its renewal cron ONLY through ``fetchCronIntegration`` (the GUI
        settings page calls it); saving ``autoRenewal=1`` through the API alone leaves
        ``UpdateCron`` empty and nothing ever renews (prod, 2026-09-09). ``cron=True`` POSTs
        that endpoint after the settings converge: ``result=new`` → changed (job created or
        re-linked), ``no change`` → noop. Requires ``enabled=1`` and ``autoRenewal=1``.
        """
        result = await super().ensure(state, params or {}, check_mode=check_mode)
        if not cron or check_mode:
            return result
        body = await self._client.post(self._cron_endpoint)
        outcome = str(body.get("result", "")).strip().lower()
        if outcome == "new":
            logger.info(
                "acme auto-renewal cron created/relinked uuid=%s",
                body.get("uuid"),
                extra={"action": "cron_created", "endpoint": self._cron_endpoint},
            )
            return EnsureResult(
                changed=True,
                action="updated" if result.changed else "cron_created",
                before=result.before,
                after={**(result.after or {}), "UpdateCron": str(body.get("uuid", ""))},
            )
        if outcome and outcome != "no change":
            raise OpnsenseServerError(
                f"acme cron integration refused: {outcome}", endpoint=self._cron_endpoint
            )
        return result

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ACME settings manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def get(self) -> dict[str, Any]:
        """Fetch the current ACME ``settings`` block.

        The ``settings/get`` payload nests the plugin config under ``settings``;
        we unwrap it so callers diff a flat dict.

        Returns:
            The ``settings`` dict (empty dict if absent).
        """
        body = await super().get()
        settings = body.get("settings", {})
        return settings if isinstance(settings, dict) else {}

    async def set(
        self,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Update the ACME ``settings`` (fetch → diff → POST only if drifted).

        Keeps ``before`` and ``params`` in the same flat ``settings`` shape for
        diffing, while nesting under ``settings`` on the POST body the API
        requires: ``{"acmeclient": {"settings": {...}}}``.

        Args:
            params:     Desired ``settings`` (flat dict).
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
                {self._payload_key: {"settings": params}},
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
