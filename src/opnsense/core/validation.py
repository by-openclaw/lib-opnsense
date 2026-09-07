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

# Port patterns — used by validate_port and validate_port_or_alias
_PORT_SINGLE_RE = re.compile(r"^\d{1,5}$")
_PORT_RANGE_RE = re.compile(r"^(\d{1,5}):(\d{1,5})$")
_ALIAS_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


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


def normalize_multi_select(value: Any) -> str:
    """Normalise a multi-select field to the CSV string the API expects on ``set``.

    OPNsense multi-select fields (interface lists, DNS server lists, …) are
    written as comma-separated strings. Accepts a string passthrough or a
    list/tuple/set of ids; ``None`` becomes ``""``.

    Args:
        value: A CSV string, an iterable of ids, or ``None``.

    Returns:
        The comma-separated string form.
    """
    if isinstance(value, list | tuple | set):
        return ",".join(str(x) for x in value)
    return str(value) if value is not None else ""


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
    """Validate IPv4 or IPv6 address using stdlib ipaddress.

    Optional spec keys for classification:
        version:   4 or 6 — restrict to IPv4-only or IPv6-only
        scope:     "private", "public", "unicast", "multicast", "loopback", "link_local"
                   — reject addresses outside the specified scope

    Examples::

        {"type": "ip"}                          # any valid IP
        {"type": "ip", "version": 4}            # IPv4 only
        {"type": "ip", "scope": "private"}      # RFC 1918 / ULA only
        {"type": "ip", "scope": "unicast"}      # no multicast, no loopback
    """
    # Handle IP/CIDR notation (e.g. 10.11.99.1/32 from VIP)
    addr_str = value.split("/")[0] if "/" in value else value

    try:
        addr = ipaddress.ip_address(addr_str)
    except ValueError:
        raise FieldValidationError(field, value, "must be a valid IP address") from None

    # Version restriction
    required_version = spec.get("version")
    if required_version is not None and addr.version != required_version:
        raise FieldValidationError(
            field, value, f"must be IPv{required_version}, got IPv{addr.version}"
        )

    # Scope restriction
    scope = spec.get("scope")
    if scope == "private" and not addr.is_private:
        raise FieldValidationError(field, value, "must be a private IP address")
    elif scope == "public" and addr.is_private:
        raise FieldValidationError(field, value, "must be a public IP address")
    elif scope == "unicast" and (addr.is_multicast or addr.is_loopback):
        raise FieldValidationError(field, value, "must be a unicast IP address")
    elif scope == "multicast" and not addr.is_multicast:
        raise FieldValidationError(field, value, "must be a multicast IP address")
    elif scope == "loopback" and not addr.is_loopback:
        raise FieldValidationError(field, value, "must be a loopback IP address")
    elif scope == "link_local" and not addr.is_link_local:
        raise FieldValidationError(field, value, "must be a link-local IP address")


def validate_cidr(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate CIDR notation (e.g. 10.0.0.0/24) using stdlib ipaddress.

    Optional spec keys:
        version: 4 or 6 — restrict to IPv4-only or IPv6-only
    """
    try:
        net = ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise FieldValidationError(
            field, value, "must be valid CIDR notation (e.g. 10.0.0.0/24)"
        ) from None

    required_version = spec.get("version")
    if required_version is not None and net.version != required_version:
        raise FieldValidationError(
            field, value, f"must be IPv{required_version} CIDR, got IPv{net.version}"
        )


def validate_mac(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate MAC address format (xx:xx:xx:xx:xx:xx)."""
    if not _MAC_RE.match(value):
        raise FieldValidationError(field, value, "must be a MAC address (xx:xx:xx:xx:xx:xx)")


def _check_port_in_range(field: str, value: str, port_str: str) -> None:
    """Check a single port number is 1-65535."""
    port_i = int(port_str)
    if not 1 <= port_i <= 65535:
        raise FieldValidationError(field, value, f"port {port_i} out of range 1-65535")


def validate_port(field: str, value: str, spec: dict[str, Any]) -> None:
    r"""Validate strict numeric port — used by WireGuard, OpenVPN, syslog, D-NAT local-port.

    Accepts:
        - Single port: ``443``
        - Range: ``80:443`` (colon-separated, both ends 1-65535)

    Rejects:
        - Alias names, comma-separated, negative, zero, >65535, non-numeric.

    Regex: ``^\\d{1,5}$`` or ``^(\\d{1,5}):(\\d{1,5})$``
    """
    m_range = _PORT_RANGE_RE.match(value)
    if m_range:
        _check_port_in_range(field, value, m_range.group(1))
        _check_port_in_range(field, value, m_range.group(2))
        return

    m_single = _PORT_SINGLE_RE.match(value)
    if m_single:
        _check_port_in_range(field, value, value)
        return

    raise FieldValidationError(field, value, "must be numeric port (1-65535) or range (80:443)")


def validate_port_or_alias(field: str, value: str, spec: dict[str, Any]) -> None:
    r"""Validate port, range, or OPNsense alias name — used by FW filter/shaper port fields.

    Accepts (per OPNsense PortField MVC model):
        - Single port: ``443``
        - Range: ``80:443``
        - Alias name: ``MyPorts``, ``inttest_web_ports``

    NOTE on filter rules (FwFilterManager):
        OPNsense 26.1.5 filter rules reject inline ranges and comma-lists.
        Use port aliases instead. See docs/port-field-reference.md.
        This validator accepts ranges because the MVC PortField type does —
        the endpoint-specific restriction is enforced server-side.

    Regex: ``^\\d{1,5}$`` | ``^(\\d{1,5}):(\\d{1,5})$`` | ``^[a-zA-Z_][a-zA-Z0-9_]*$``
    """
    # Try each valid format via regex
    m_range = _PORT_RANGE_RE.match(value)
    if m_range:
        _check_port_in_range(field, value, m_range.group(1))
        _check_port_in_range(field, value, m_range.group(2))
        return

    m_single = _PORT_SINGLE_RE.match(value)
    if m_single:
        _check_port_in_range(field, value, value)
        return

    if _ALIAS_RE.match(value):
        return  # valid alias name

    raise FieldValidationError(
        field, value, "must be port (1-65535), range (80:443), or alias name"
    )


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


def validate_dict(field: str, value: str, spec: dict[str, Any]) -> None:
    """Validate a nested dict field with optional sub-field specs.

    The value parameter is ignored for dict validation — the actual dict
    is validated in ValidatorRegistry.validate_params() which handles
    dict types specially (passes the dict, not str(dict)).
    """


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
            "port_or_alias": validate_port_or_alias,
            "hostname": validate_hostname,
            "dict": validate_dict,
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
                field_type = spec.get("type", "str")

                # Dict fields — validate sub-fields recursively
                if field_type == "dict":
                    if value is None or value == "":
                        if required:
                            raise FieldValidationError(
                                field, value, "required field is missing or empty"
                            )
                        continue
                    if not isinstance(value, dict):
                        raise FieldValidationError(field, value, "must be a dict")
                    sub_validators = spec.get("fields", {})
                    if sub_validators:
                        self.validate_params(value, sub_validators)
                    continue

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
