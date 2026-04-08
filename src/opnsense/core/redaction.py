# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unified field redaction with configurable reveal depth.

Replaces both BaseManager._redact() and logging._redact_value() with a
single implementation. logging.py delegates to this module.

Zero imports from managers/ or client.py — independently reusable.

Redaction rules: ``(reveal_start, reveal_end, mask_char)``
    - ``(0, 0, "*")`` — full redaction → ``<REDACTED:field>``
    - ``(0, 4, "*")`` — last 4 visible → ``***...ExQi``
    - ``(4, 4, "*")`` — first 4 + last 4 → ``gTCJ***igCn``
    - ``(8, 0, "*")`` — first 8 visible → ``ssh-ed25***``

Usage::

    from opnsense.core.redaction import Redactor

    redactor = Redactor(rules=REDACT_RULES)
    safe = redactor.redact_dict(data, redact_fields={"password", "api_key"})
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default redaction rules matching OPNsense field sensitivity
DEFAULT_RULES: dict[str, tuple[int, int, str]] = {
    "password": (0, 0, "*"),
    "otp_seed": (0, 0, "*"),
    "scrambled_password": (0, 0, "*"),
    "authorizedkeys": (8, 0, "*"),
    "secret": (0, 4, "*"),
    "api_key": (4, 4, "*"),
    "key": (4, 4, "*"),
}


class Redactor:
    """Configurable field redactor with partial reveal support.

    Args:
        rules: Dict mapping field name patterns to
               ``(reveal_start, reveal_end, mask_char)`` tuples.
               Defaults to :data:`DEFAULT_RULES`.
    """

    def __init__(self, rules: dict[str, tuple[int, int, str]] | None = None) -> None:
        """Initialise with optional custom redaction rules."""
        self._rules = rules if rules is not None else DEFAULT_RULES

    @property
    def rules(self) -> dict[str, tuple[int, int, str]]:
        """Return the active redaction rules."""
        return dict(self._rules)

    def redact_value(self, key: str, value: Any) -> Any:
        """Redact a single value based on its field name.

        Matches the longest rule pattern found in the key name (case-insensitive).
        Values shorter than the reveal window are fully redacted.

        Args:
            key:   Field name to match against rules.
            value: The value to potentially redact.

        Returns:
            The original value if no rule matches, otherwise redacted string.
        """
        try:
            key_lower = key.lower()
            matched_rule: tuple[int, int, str] | None = None
            matched_len = 0
            for pattern, rule in self._rules.items():
                if pattern in key_lower and len(pattern) > matched_len:
                    matched_rule = rule
                    matched_len = len(pattern)

            if matched_rule is None:
                return value

            if not isinstance(value, str) or not value:
                return f"<REDACTED:{key}>"

            reveal_start, reveal_end, mask_char = matched_rule

            if reveal_start == 0 and reveal_end == 0:
                return f"<REDACTED:{key}>"

            val_len = len(value)
            if val_len <= reveal_start + reveal_end:
                return f"<REDACTED:{key}>"

            prefix = value[:reveal_start] if reveal_start > 0 else ""
            suffix = value[-reveal_end:] if reveal_end > 0 else ""
            masked_len = val_len - reveal_start - reveal_end
            return f"{prefix}{mask_char * masked_len}{suffix}"
        except Exception as exc:
            logger.error(
                "redact_value failed for key=%s: %s",
                key,
                exc,
                extra={"action": "redact_value_failed", "error": str(exc)},
            )
            raise

    def redact_dict(
        self,
        data: dict[str, Any],
        redact_fields: set[str] | None = None,
    ) -> dict[str, Any]:
        """Deep-redact fields from a data dict.

        When ``redact_fields`` is provided, only those exact field names are
        redacted (simple replacement with ``<REDACTED:field>``). When omitted,
        all fields are checked against redaction rules for partial reveal.

        Args:
            data:          Resource data dict to redact.
            redact_fields: Optional set of field names for simple full redaction.

        Returns:
            A deep copy of the dict with sensitive fields redacted.
        """
        try:
            redacted = copy.deepcopy(data)

            if redact_fields is not None:
                for key in redact_fields:
                    if key in redacted:
                        redacted[key] = f"<REDACTED:{key}>"
                return redacted

            return {k: self.redact_value(k, v) for k, v in redacted.items()}
        except Exception as exc:
            logger.error(
                "redact_dict failed: %s",
                exc,
                extra={"action": "redact_dict_failed", "error": str(exc)},
            )
            raise

    def structlog_processor(
        self,
        _logger: Any,  # noqa: ANN401
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Structlog processor that redacts sensitive fields in every log event.

        Drop-in replacement for the processor in logging.py.

        Args:
            _logger:     The logger instance (unused, required by structlog).
            method_name: The log method name (unused, required by structlog).
            event_dict:  The structlog event dictionary.

        Returns:
            Event dict with sensitive field values redacted.
        """
        try:
            return {k: self.redact_value(k, v) for k, v in event_dict.items()}
        except Exception as exc:
            logger.error(
                "structlog_processor failed: %s",
                exc,
                extra={"action": "structlog_processor_failed", "error": str(exc)},
            )
            raise
