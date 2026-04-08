# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Field validators — client-side validation before API calls.

Validates params against OPNsense MVC model field types and constraints.
Catches bad input early with clear error messages — no wasted round-trips.

Field type reference:
    https://docs.opnsense.org/development/frontend/models_fieldtypes.html
    https://docs.opnsense.org/development/frontend/models_constraints.html

Usage::

    from opnsense.validators import validate_params

    validators = {
        "name": {"type": "str", "required": True, "max_length": 32, "regex": r"^[a-zA-Z0-9_]+$"},
        "action": {"type": "enum", "values": ["pass", "block", "reject"]},
        "enabled": {"type": "bool_str"},
    }

    validate_params(params, validators)  # raises FieldValidationError on failure
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any


class FieldValidationError(ValueError):
    """A field failed client-side validation.

    Attributes:
        field:    Field name that failed.
        value:    The invalid value.
        rule:     Description of the violated constraint.
    """

    def __init__(self, field: str, value: Any, rule: str) -> None:
        """Initialise with field context.

        Args:
            field: Field name.
            value: The invalid value provided.
            rule:  Human-readable constraint description.
        """
        self.field = field
        self.value = value
        self.rule = rule
        super().__init__(f"Invalid field '{field}': {rule} (got: {value!r})")


# -- Built-in type validators ------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_COLOR_RE = re.compile(r"^[0-9a-fA-F]{6}$")
_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$")


def _validate_str(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate a string field: max_length, regex."""
    max_length = spec.get("max_length", 255)
    if len(value) > max_length:
        raise FieldValidationError(field, value, f"max length {max_length}, got {len(value)}")

    regex = spec.get("regex")
    if regex and not re.match(regex, value):
        raise FieldValidationError(field, value, f"must match pattern {regex}")


def _validate_enum(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate against a fixed list of allowed values."""
    values = spec.get("values", [])
    if value not in values:
        raise FieldValidationError(field, value, f"must be one of {values}")


def _validate_int(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate integer: format + min/max range."""
    try:
        num = int(value)
    except (ValueError, TypeError):
        raise FieldValidationError(field, value, "must be an integer") from None

    min_val = spec.get("min")
    max_val = spec.get("max")
    if min_val is not None and num < min_val:
        raise FieldValidationError(field, value, f"minimum {min_val}")
    if max_val is not None and num > max_val:
        raise FieldValidationError(field, value, f"maximum {max_val}")


def _validate_bool_str(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate OPNsense boolean string: '0' or '1' only."""
    if value not in ("0", "1"):
        raise FieldValidationError(field, value, "must be '0' or '1'")


def _validate_email(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate email address format."""
    if not _EMAIL_RE.match(value):
        raise FieldValidationError(field, value, "must be a valid email address")


def _validate_ip(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate IPv4 or IPv6 address using stdlib ipaddress."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise FieldValidationError(field, value, "must be a valid IP address") from None


def _validate_cidr(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate CIDR notation (e.g. 10.0.0.0/24) using stdlib ipaddress."""
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise FieldValidationError(
            field, value, "must be valid CIDR notation (e.g. 10.0.0.0/24)"
        ) from None


def _validate_mac(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate MAC address format (xx:xx:xx:xx:xx:xx)."""
    if not _MAC_RE.match(value):
        raise FieldValidationError(field, value, "must be a MAC address (xx:xx:xx:xx:xx:xx)")


def _validate_port(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate port number (1-65535) or port range (80:443)."""
    for part in value.split(","):
        part = part.strip()
        if ":" in part:
            low, high = part.split(":", 1)
            try:
                if not (1 <= int(low) <= 65535 and 1 <= int(high) <= 65535):
                    raise FieldValidationError(field, value, "port range must be 1-65535")
            except ValueError:
                raise FieldValidationError(field, value, "port range must be numeric") from None
        else:
            try:
                if not 1 <= int(part) <= 65535:
                    raise FieldValidationError(field, value, "port must be 1-65535")
            except ValueError:
                raise FieldValidationError(field, value, "port must be numeric") from None


def _validate_color(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate hex color (6 digits, no # prefix)."""
    if not _COLOR_RE.match(value):
        raise FieldValidationError(field, value, "must be 6 hex digits (no # prefix)")


def _validate_hostname(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate hostname per RFC 952/1123."""
    if not _HOSTNAME_RE.match(value):
        raise FieldValidationError(
            field, value, "must be a valid hostname (alphanumeric + hyphens)"
        )


# -- Type dispatch table ------------------------------------------------------

_TYPE_VALIDATORS: dict[str, Any] = {
    "str": _validate_str,
    "enum": _validate_enum,
    "int": _validate_int,
    "bool_str": _validate_bool_str,
    "email": _validate_email,
    "ip": _validate_ip,
    "cidr": _validate_cidr,
    "mac": _validate_mac,
    "port": _validate_port,
    "color": _validate_color,
    "hostname": _validate_hostname,
}


# -- Public API ---------------------------------------------------------------


def validate_params(
    params: dict[str, Any],
    validators: dict[str, dict[str, Any]],
) -> None:
    """Validate params dict against field validators.

    Args:
        params:     The params dict to validate.
        validators: Field validator specs — {field_name: {type, required, ...}}.

    Raises:
        FieldValidationError: If any field fails validation.
    """
    for field, spec in validators.items():
        required = spec.get("required", False)
        value = params.get(field)

        # Required check
        if value is None or (isinstance(value, str) and value == ""):
            if required:
                raise FieldValidationError(field, value, "required field is missing or empty")
            continue  # Optional and not provided — skip

        # Type-specific validation
        value_str = str(value)
        field_type = spec.get("type", "str")
        validator_fn = _TYPE_VALIDATORS.get(field_type)
        if validator_fn is not None:
            validator_fn(field, value_str, spec)
