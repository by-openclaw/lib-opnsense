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

from opnsense.core.redaction import DEFAULT_RULES, Redactor

# Backward compatibility — re-export for consumers that import REDACT_RULES from here
REDACT_RULES = DEFAULT_RULES

# Shared redactor instance for the structlog processor
_redactor = Redactor()


def _redact_value(key: str, value: Any) -> Any:
    """Redact a single value based on its field name.

    Delegates to :class:`~opnsense.core.redaction.Redactor`.
    Kept for backward compatibility.
    """
    return _redactor.redact_value(key, value)


def _redact_processor(
    logger: Any,  # noqa: ANN401
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Structlog processor that redacts sensitive fields in every log event."""
    return _redactor.structlog_processor(logger, method_name, event_dict)


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

    # Console handler — always JSON (Loki-compatible on stderr too)
    # colorize param adds a second human-readable handler when True
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(log_level)
    console.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    )
    stdlib_root.addHandler(console)

    # Optional colorized handler for local dev (stdout, not stderr)
    if colorize:
        color_console = logging.StreamHandler(sys.stdout)
        color_console.setLevel(log_level)
        color_console.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(colors=True),
                foreign_pre_chain=shared_processors,
            )
        )
        stdlib_root.addHandler(color_console)

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
