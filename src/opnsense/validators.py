# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Backward-compatibility shim — delegates to core/validation.py.

Canonical locations:
    - FieldValidationError → opnsense.exceptions
    - validate_params      → opnsense.core.validation.ValidatorRegistry.validate_params
    - Built-in validators  → opnsense.core.validation (validate_str, validate_enum, ...)

This module is kept for backward compatibility only. New code should
import from ``opnsense.exceptions`` and ``opnsense.core.validation``.
"""

from __future__ import annotations

from typing import Any

from opnsense.core.validation import ValidatorRegistry
from opnsense.exceptions import FieldValidationError

__all__ = ["FieldValidationError", "validate_params"]

# Shared registry instance for the module-level validate_params function
_registry = ValidatorRegistry()


def validate_params(
    params: dict[str, Any],
    validators: dict[str, dict[str, Any]],
) -> None:
    """Validate params dict against field validators.

    Delegates to :meth:`~opnsense.core.validation.ValidatorRegistry.validate_params`.

    Args:
        params:     The params dict to validate.
        validators: Field validator specs — {field_name: {type, required, ...}}.

    Raises:
        FieldValidationError: If any field fails validation.
    """
    _registry.validate_params(params, validators)
