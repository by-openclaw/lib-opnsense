# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Singleton settings base — fetch/diff/set for OPNsense singleton config objects.

Many OPNsense modules expose a single config document (not a list of resources)
via ``GET {module}/settings/get`` + ``POST {module}/settings/set``. There is no
UUID, no add/del, no list. Examples: ``dnsmasq``, ``radvd``, ``unbound``,
``kea/dhcpv4/general``, ``ids``, ``syslog``, ``routing``, ``wireguard/general``.

`BaseManager` cannot serve these because it assumes ``searchX``/``addX``/``setX``/
``delX`` with UUIDs and ``_match_keys``. This module supplies the missing
pattern: fetch current settings, diff against desired, POST only if drifted,
reconfigure if needed — same idempotency contract, no UUID.

Logging contract — every ``ensure()`` outcome logs ``before`` / ``after`` /
``changed`` / ``duration_ms`` per ADR ``lib/python/0001 §8``.

Severity: DEBUG=noop, INFO=update (a singleton can only update — it cannot be
created or deleted), ERROR=failure.

See: ADR ``lib/python/0001-design-standard.md``, epic
``https://github.com/by-openclaw/lib-opnsense/issues/65``.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.diff import DiffEngine
from opnsense.core.logging_helpers import ManagerLogBuilder
from opnsense.core.redaction import Redactor
from opnsense.core.validation import ValidatorRegistry
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)

_diff_engine = DiffEngine()
_redactor = Redactor()
_validator_registry = ValidatorRegistry()


class BaseSingletonManager(ABC):
    """Abstract base for OPNsense singleton settings managers.

    INPUT (subclass declarations):
        _endpoint:       Settings domain path (e.g. ``'dnsmasq/settings'``).
        _payload_key:    Top-level JSON key for ``get``/``set`` payloads
                         (e.g. ``'dnsmasq'``). The API wraps both the
                         response and the request body under this key.
        _apply_endpoint: Reconfigure endpoint, or ``None`` if the daemon
                         applies settings immediately on ``set``.
        _section:        Optional sub-block under the payload key that this
                         manager owns (e.g. ``'general'`` when the document is
                         ``{"unbound": {"general": {...}, "advanced": {...}}}``).
                         ``get`` unwraps it so callers diff a flat dict; ``set``
                         re-nests it on the POST body. ``None`` = flat payload.
        _validators:     Field validators dict (same schema as BaseManager).
        REDACT_FIELDS:   Field names to redact in before/after diff + logs.
        _apply_timeout:  Optional per-manager apply timeout (seconds).

    OUTPUT (``EnsureResult``):
        changed:  True if the singleton state was modified.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always ``None`` (singletons have no UUID).
        before:   Redacted dict of settings before the call.
        after:    Redacted dict of settings after the call (or desired-after
                  in ``check_mode``).
    """

    _endpoint: str
    _payload_key: str
    _apply_endpoint: str | None = None
    _section: str | None = None
    _apply_timeout: int | None = None
    _validators: dict[str, dict[str, Any]] = {}

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the singleton manager with an OpnsenseClient.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get(self) -> dict[str, Any]:
        """Fetch the current singleton settings.

        Returns:
            The inner payload dict (unwrapped from ``_payload_key``).
        """
        try:
            body = await self._client.get(f"{self._endpoint}/get")
        except Exception as exc:
            logger.error(
                "get failed %s: %s",
                self._endpoint,
                exc,
                extra={
                    "action": "get_failed",
                    "endpoint": self._endpoint,
                    "error": str(exc),
                },
            )
            raise
        inner = body.get(self._payload_key, body)
        if self._section is None:
            return inner
        section = inner.get(self._section, {}) if isinstance(inner, dict) else {}
        return section if isinstance(section, dict) else {}

    async def set(
        self,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Update the singleton settings (fetch → diff → POST only if drifted).

        Args:
            params:     Desired settings (merged into existing on the server side).
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
                extra=log.build_extra(
                    "noop",
                    {},
                    before=redacted_before,
                    changed=False,
                ),
            )
            return EnsureResult(
                changed=False,
                action="noop",
                before=redacted_before,
                after=redacted_before,
            )

        # Merge desired over current to produce the projected after-state
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
            payload = {self._section: params} if self._section is not None else params
            await self._client.post(
                f"{self._endpoint}/set",
                {self._payload_key: payload},
            )
            await self._apply()
        except Exception as exc:
            logger.error(
                "set failed %s: %s",
                self._endpoint,
                exc,
                extra=log.build_extra(
                    "update_failed",
                    {},
                    before=redacted_before,
                    error=str(exc),
                ),
            )
            raise

        # Re-fetch to get the canonical after-state from the server
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

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure the singleton settings match the desired params.

        A singleton config cannot be created or deleted — only updated —
        so only ``state='present'`` is supported.

        Args:
            state:      Must be ``'present'``. ``'absent'`` raises ValueError.
            params:     Desired settings.
            check_mode: If True, return what would happen without making changes.

        Returns:
            ``EnsureResult`` describing what was (or would be) done.

        Raises:
            ValueError: If ``state != 'present'``.
            FieldValidationError: If any field fails client-side validation.
        """
        if state != "present":
            raise ValueError(f"Singleton managers only support state='present'. Got: {state!r}")

        if self._validators:
            try:
                _validator_registry.validate_params(params, self._validators)
            except Exception as exc:
                logger.error(
                    "validation failed %s: %s",
                    self.__class__.__name__,
                    exc,
                    extra={
                        "action": "validation_failed",
                        "endpoint": self._endpoint,
                        "error": str(exc),
                    },
                )
                raise

        return await self.set(params, check_mode=check_mode)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _apply(self) -> None:
        """Trigger reconfigure if ``_apply_endpoint`` is set."""
        if self._apply_endpoint is not None:
            try:
                await self._client.reconfigure(
                    self._apply_endpoint,
                    timeout=self._apply_timeout,
                )
            except Exception as exc:
                logger.error(
                    "apply failed %s: %s",
                    self._apply_endpoint,
                    exc,
                    extra={
                        "action": "apply_failed",
                        "endpoint": self._apply_endpoint,
                        "error": str(exc),
                    },
                )
                raise
