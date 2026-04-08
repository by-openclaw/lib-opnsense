# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Field validation — protocol, registry, and built-in types.

Validates params against OPNsense MVC model field types and constraints.
Catches bad input early with clear error messages — no wasted round-trips.

Zero imports from managers/ or client.py — independently reusable.

Field type reference:
    https://docs.opnsense.org/development/frontend/models_fieldtypes.html
    https://docs.opnsense.org/development/frontend/models_constraints.html

Usage::

    from opnsense.core.validation import ValidatorRegistry

    registry = ValidatorRegistry()
    registry.validate_params(params, validators)
"""

from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any, Protocol, runtime_checkable

from opnsense.exceptions import FieldValidationError

logger = logging.getLogger(__name__)

# -- Compiled regex patterns ---------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_COLOR_RE = re.compile(r"^[0-9a-fA-F]{6}$")
_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$")


# -- FieldValidator protocol --------------------------------------------------


@runtime_checkable
class FieldValidator(Protocol):
    """Protocol for field validators.

    Implementations validate a single field value against a spec dict.
    Raise FieldValidationError on failure, return None on success.
    """

    def __call__(self, field: str, value: str, spec: dict[str, Any]) -> None:
        """Validate a field value against a spec."""
        ...


# -- Built-in validators -------------------------------------------------------


def validate_str(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate a string field: max_length, regex."""
    max_length = spec.get("max_length", 255)
    if len(value) > max_length:
        raise FieldValidationError(field, value, f"max length {max_length}, got {len(value)}")

    regex = spec.get("regex")
    if regex and not re.match(regex, value):
        raise FieldValidationError(field, value, f"must match pattern {regex}")


def validate_enum(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate against a fixed list of allowed values."""
    values = spec.get("values", [])
    if value not in values:
        raise FieldValidationError(field, value, f"must be one of {values}")


def validate_int(field: str, value: str, spec: dict[str, Any]) -> None:
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


def validate_bool_str(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate OPNsense boolean string: '0' or '1' only."""
    if value not in ("0", "1"):
        raise FieldValidationError(field, value, "must be '0' or '1'")


def validate_email(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate email address format."""
    if not _EMAIL_RE.match(value):
        raise FieldValidationError(field, value, "must be a valid email address")


def validate_ip(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate IPv4 or IPv6 address using stdlib ipaddress."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise FieldValidationError(field, value, "must be a valid IP address") from None


def validate_cidr(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate CIDR notation (e.g. 10.0.0.0/24) using stdlib ipaddress."""
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise FieldValidationError(
            field, value, "must be valid CIDR notation (e.g. 10.0.0.0/24)"
        ) from None


def validate_mac(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate MAC address format (xx:xx:xx:xx:xx:xx)."""
    if not _MAC_RE.match(value):
        raise FieldValidationError(field, value, "must be a MAC address (xx:xx:xx:xx:xx:xx)")


def validate_port(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate port number (1-65535) or port range (80:443)."""
    for part in value.split(","):
        part = part.strip()
        if ":" in part:
            low_s, high_s = part.split(":", 1)
            try:
                low_i, high_i = int(low_s), int(high_s)
            except ValueError:
                raise FieldValidationError(field, value, "port range must be numeric") from None
            if not (1 <= low_i <= 65535 and 1 <= high_i <= 65535):
                raise FieldValidationError(field, value, "port range must be 1-65535")
        else:
            try:
                port_i = int(part)
            except ValueError:
                raise FieldValidationError(field, value, "port must be numeric") from None
            if not 1 <= port_i <= 65535:
                raise FieldValidationError(field, value, "port must be 1-65535")


def validate_color(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate hex color (6 digits, no # prefix)."""
    if not _COLOR_RE.match(value):
        raise FieldValidationError(field, value, "must be 6 hex digits (no # prefix)")


def validate_hostname(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate hostname per RFC 952/1123."""
    if not _HOSTNAME_RE.match(value):
        raise FieldValidationError(
            field, value, "must be a valid hostname (alphanumeric + hyphens)"
        )


# -- Validator registry --------------------------------------------------------


class ValidatorRegistry:
    """Extensible registry of field validators.

    Pre-loaded with all built-in OPNsense field types.
    Custom validators can be registered without modifying source.

    Usage::

        registry = ValidatorRegistry()
        registry.register("custom_type", my_validator_fn)
        registry.validate_params(params, validators)
    """

    def __init__(self) -> None:
        """Initialise with all built-in OPNsense field type validators."""
        self._validators: dict[str, FieldValidator] = {
            "str": validate_str,
            "enum": validate_enum,
            "int": validate_int,
            "bool_str": validate_bool_str,
            "email": validate_email,
            "ip": validate_ip,
            "cidr": validate_cidr,
            "mac": validate_mac,
            "port": validate_port,
            "color": validate_color,
            "hostname": validate_hostname,
        }

    def register(self, type_name: str, validator: FieldValidator) -> None:
        """Register a custom validator for a field type.

        Args:
            type_name: Type identifier (used in validator specs).
            validator: Callable implementing the FieldValidator protocol.
        """
        try:
            self._validators[type_name] = validator
        except Exception as exc:
            logger.error(
                "register failed for type=%s: %s",
                type_name,
                exc,
                extra={"action": "register_failed", "error": str(exc)},
            )
            raise

    def get(self, type_name: str) -> FieldValidator | None:
        """Get a validator by type name.

        Args:
            type_name: Type identifier.

        Returns:
            The validator callable, or None if not registered.
        """
        try:
            return self._validators.get(type_name)
        except Exception as exc:
            logger.error(
                "get failed for type=%s: %s",
                type_name,
                exc,
                extra={"action": "get_validator_failed", "error": str(exc)},
            )
            raise

    def validate_params(
        self,
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
        try:
            for field, spec in validators.items():
                required = spec.get("required", False)
                value = params.get(field)

                if value is None or (isinstance(value, str) and value == ""):
                    if required:
                        raise FieldValidationError(
                            field, value, "required field is missing or empty"
                        )
                    continue

                value_str = str(value)
                field_type = spec.get("type", "str")
                validator_fn = self._validators.get(field_type)
                if validator_fn is not None:
                    try:
                        validator_fn(field, value_str, spec)
                    except FieldValidationError:
                        raise
                    except Exception as exc:
                        raise FieldValidationError(
                            field, value_str, f"validation error: {exc}"
                        ) from exc
        except FieldValidationError:
            raise
        except Exception as exc:
            logger.error(
                "validate_params failed: %s",
                exc,
                extra={"action": "validate_params_failed", "error": str(exc)},
            )
            raise
