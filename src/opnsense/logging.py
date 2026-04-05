# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Structured logging — Loki/Promtail compatible via structlog.

Console: colorized by severity (structlog ConsoleRenderer).
File:    one JSON line per event (structlog JSONRenderer) for Loki ingestion.
All sensitive fields auto-redacted with configurable reveal depth.

Usage::

    from opnsense.logging import configure_logging

    configure_logging(level="INFO", log_file="logs/opnsense.log")
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Redaction rules: pattern -> (reveal_start, reveal_end, mask_char)
#
#   password:       full redaction        -> <REDACTED:password>
#   secret:         last 4 visible        -> ***...ExQi
#   api_key / key:  first 4 + last 4      -> gTCJ***...igCn
#   authorizedkeys: first 8 visible       -> ssh-ed25***...
#   otp_seed:       full redaction        -> <REDACTED:otp_seed>
# ---------------------------------------------------------------------------
REDACT_RULES: dict[str, tuple[int, int, str]] = {
    "password": (0, 0, "*"),
    "otp_seed": (0, 0, "*"),
    "scrambled_password": (0, 0, "*"),
    "authorizedkeys": (8, 0, "*"),
    "secret": (0, 4, "*"),
    "api_key": (4, 4, "*"),
    "key": (4, 4, "*"),
}


def _redact_value(key: str, value: Any) -> Any:
    """Redact a single value based on its field name.

    Matches the longest REDACT_RULES pattern found in the key name.
    Values shorter than the reveal window are fully redacted.
    """
    key_lower = key.lower()
    matched_rule: tuple[int, int, str] | None = None
    matched_len = 0
    for pattern, rule in REDACT_RULES.items():
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


def _redact_processor(
    logger: Any,  # noqa: ANN401
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Structlog processor that redacts sensitive fields in every log event."""
    return {k: _redact_value(k, v) for k, v in event_dict.items()}


def configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
    service: str = "lib-opnsense",
    colorize: bool = True,
) -> None:
    """Configure structured logging for all lib-opnsense loggers.

    Args:
        level:    Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path for JSON log output (Loki-compatible).
        service:  Service label added to every event for Loki filtering.
        colorize: Colorized console output (default True). False for JSON-only.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors — run before rendering
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),  # stdlib extra={} -> structlog event_dict
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _redact_processor,
        structlog.processors.EventRenamer("msg"),
    ]

    # --- stdlib logging (for file handler + compatibility) ---
    stdlib_root = logging.getLogger("opnsense")
    stdlib_root.setLevel(log_level)
    stdlib_root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(log_level)
    if colorize:
        console.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(colors=True),
                foreign_pre_chain=shared_processors,
            )
        )
    else:
        console.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=shared_processors,
            )
        )
    stdlib_root.addHandler(console)

    # File handler — always JSON for Loki
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=shared_processors,
            )
        )
        stdlib_root.addHandler(file_handler)

    # --- structlog configuration ---
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
