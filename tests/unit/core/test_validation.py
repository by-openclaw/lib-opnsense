# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for core/validation.py — ValidatorRegistry + FieldValidator protocol."""

from __future__ import annotations

from typing import Any

import pytest

from opnsense.core.validation import FieldValidator, ValidatorRegistry, validate_str
from opnsense.exceptions import FieldValidationError


class TestValidatorRegistry:
    """ValidatorRegistry dispatches to built-in and custom validators."""

    def setup_method(self) -> None:
        self.registry = ValidatorRegistry()

    def test_str_valid(self) -> None:
        self.registry.validate_params({"name": "rune"}, {"name": {"type": "str", "max_length": 32}})

    def test_str_too_long(self) -> None:
        with pytest.raises(FieldValidationError, match="max length 5"):
            self.registry.validate_params(
                {"name": "toolong"}, {"name": {"type": "str", "max_length": 5}}
            )

    def test_str_regex_fail(self) -> None:
        with pytest.raises(FieldValidationError, match="must match pattern"):
            self.registry.validate_params(
                {"name": "bad name!"}, {"name": {"type": "str", "regex": r"^[a-z]+$"}}
            )

    def test_enum_valid(self) -> None:
        self.registry.validate_params(
            {"action": "pass"}, {"action": {"type": "enum", "values": ["pass", "block"]}}
        )

    def test_enum_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="must be one of"):
            self.registry.validate_params(
                {"action": "drop"}, {"action": {"type": "enum", "values": ["pass", "block"]}}
            )

    def test_int_valid(self) -> None:
        self.registry.validate_params(
            {"tag": "100"}, {"tag": {"type": "int", "min": 1, "max": 4094}}
        )

    def test_int_below_min(self) -> None:
        with pytest.raises(FieldValidationError, match="minimum 1"):
            self.registry.validate_params(
                {"tag": "0"}, {"tag": {"type": "int", "min": 1, "max": 4094}}
            )

    def test_int_above_max(self) -> None:
        with pytest.raises(FieldValidationError, match="maximum 4094"):
            self.registry.validate_params(
                {"tag": "5000"}, {"tag": {"type": "int", "min": 1, "max": 4094}}
            )

    def test_int_not_numeric(self) -> None:
        with pytest.raises(FieldValidationError, match="must be an integer"):
            self.registry.validate_params({"tag": "abc"}, {"tag": {"type": "int"}})

    def test_bool_str_valid(self) -> None:
        self.registry.validate_params({"enabled": "1"}, {"enabled": {"type": "bool_str"}})
        self.registry.validate_params({"enabled": "0"}, {"enabled": {"type": "bool_str"}})

    def test_bool_str_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="must be '0' or '1'"):
            self.registry.validate_params({"enabled": "true"}, {"enabled": {"type": "bool_str"}})

    def test_email_valid(self) -> None:
        self.registry.validate_params({"email": "user@example.com"}, {"email": {"type": "email"}})

    def test_email_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="valid email"):
            self.registry.validate_params({"email": "nope"}, {"email": {"type": "email"}})

    def test_ip_valid(self) -> None:
        self.registry.validate_params({"addr": "10.0.0.1"}, {"addr": {"type": "ip"}})
        self.registry.validate_params({"addr": "::1"}, {"addr": {"type": "ip"}})

    def test_ip_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="valid IP"):
            self.registry.validate_params({"addr": "999.999.999.999"}, {"addr": {"type": "ip"}})

    def test_cidr_valid(self) -> None:
        self.registry.validate_params({"net": "10.0.0.0/24"}, {"net": {"type": "cidr"}})

    def test_cidr_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="CIDR"):
            self.registry.validate_params({"net": "nope"}, {"net": {"type": "cidr"}})

    def test_mac_valid(self) -> None:
        self.registry.validate_params({"mac": "aa:bb:cc:dd:ee:ff"}, {"mac": {"type": "mac"}})

    def test_mac_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="MAC"):
            self.registry.validate_params({"mac": "not-a-mac"}, {"mac": {"type": "mac"}})

    def test_port_valid(self) -> None:
        self.registry.validate_params({"port": "443"}, {"port": {"type": "port"}})
        self.registry.validate_params({"port": "80:443"}, {"port": {"type": "port"}})

    def test_port_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="1-65535"):
            self.registry.validate_params({"port": "0"}, {"port": {"type": "port"}})

    def test_color_valid(self) -> None:
        self.registry.validate_params({"color": "ff0000"}, {"color": {"type": "color"}})

    def test_color_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="6 hex digits"):
            self.registry.validate_params({"color": "#ff0000"}, {"color": {"type": "color"}})

    def test_hostname_valid(self) -> None:
        self.registry.validate_params({"host": "web-01"}, {"host": {"type": "hostname"}})

    def test_hostname_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="valid hostname"):
            self.registry.validate_params({"host": "-invalid"}, {"host": {"type": "hostname"}})

    def test_required_field_missing(self) -> None:
        with pytest.raises(FieldValidationError, match="required"):
            self.registry.validate_params({}, {"name": {"type": "str", "required": True}})

    def test_required_field_empty(self) -> None:
        with pytest.raises(FieldValidationError, match="required"):
            self.registry.validate_params({"name": ""}, {"name": {"type": "str", "required": True}})

    def test_optional_field_missing_passes(self) -> None:
        self.registry.validate_params({}, {"name": {"type": "str"}})


class TestCustomValidator:
    """Custom validators can be registered via registry."""

    def test_register_and_use(self) -> None:
        def validate_uuid(field: str, value: str, spec: dict[str, Any]) -> None:
            if len(value) != 36:
                raise FieldValidationError(field, value, "must be 36 chars")

        registry = ValidatorRegistry()
        registry.register("uuid", validate_uuid)
        registry.validate_params(
            {"id": "12345678-1234-1234-1234-123456789012"},
            {"id": {"type": "uuid"}},
        )

    def test_get_registered(self) -> None:
        registry = ValidatorRegistry()
        assert registry.get("str") is not None
        assert registry.get("nonexistent") is None


class TestFieldValidatorProtocol:
    """FieldValidator protocol is runtime-checkable."""

    def test_builtin_matches_protocol(self) -> None:
        assert isinstance(validate_str, FieldValidator)


class TestFieldValidationErrorAttributes:
    """FieldValidationError carries field, value, and rule."""

    def test_attributes(self) -> None:
        with pytest.raises(FieldValidationError) as exc_info:
            raise FieldValidationError("name", "bad!", "must be alphanumeric")
        err = exc_info.value
        assert err.field == "name"
        assert err.value == "bad!"
        assert err.rule == "must be alphanumeric"
