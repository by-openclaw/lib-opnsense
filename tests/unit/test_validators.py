# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.validators — field validation framework."""

from __future__ import annotations

import pytest

from opnsense.validators import FieldValidationError, validate_params


class TestStrValidator:
    """String field validation."""

    def test_valid_str(self) -> None:
        validate_params({"name": "hello"}, {"name": {"type": "str", "max_length": 10}})

    def test_str_too_long(self) -> None:
        with pytest.raises(FieldValidationError, match="max length 5"):
            validate_params({"name": "toolong"}, {"name": {"type": "str", "max_length": 5}})

    def test_str_regex_valid(self) -> None:
        validate_params({"name": "abc_123"}, {"name": {"type": "str", "regex": r"^[a-z0-9_]+$"}})

    def test_str_regex_invalid(self) -> None:
        with pytest.raises(FieldValidationError, match="must match pattern"):
            validate_params(
                {"name": "has spaces"}, {"name": {"type": "str", "regex": r"^[a-z0-9_]+$"}}
            )


class TestEnumValidator:
    """Enum field validation."""

    def test_valid_enum(self) -> None:
        validate_params(
            {"action": "pass"}, {"action": {"type": "enum", "values": ["pass", "block"]}}
        )

    def test_invalid_enum(self) -> None:
        with pytest.raises(FieldValidationError, match="must be one of"):
            validate_params(
                {"action": "bogus"}, {"action": {"type": "enum", "values": ["pass", "block"]}}
            )


class TestIntValidator:
    """Integer field validation."""

    def test_valid_int(self) -> None:
        validate_params({"tag": "100"}, {"tag": {"type": "int", "min": 1, "max": 4094}})

    def test_int_below_min(self) -> None:
        with pytest.raises(FieldValidationError, match="minimum 1"):
            validate_params({"tag": "0"}, {"tag": {"type": "int", "min": 1}})

    def test_int_above_max(self) -> None:
        with pytest.raises(FieldValidationError, match="maximum 4094"):
            validate_params({"tag": "5000"}, {"tag": {"type": "int", "max": 4094}})

    def test_int_not_numeric(self) -> None:
        with pytest.raises(FieldValidationError, match="must be an integer"):
            validate_params({"tag": "abc"}, {"tag": {"type": "int"}})


class TestBoolStrValidator:
    """OPNsense boolean string validation."""

    def test_valid_0(self) -> None:
        validate_params({"enabled": "0"}, {"enabled": {"type": "bool_str"}})

    def test_valid_1(self) -> None:
        validate_params({"enabled": "1"}, {"enabled": {"type": "bool_str"}})

    def test_invalid_bool(self) -> None:
        with pytest.raises(FieldValidationError, match="must be '0' or '1'"):
            validate_params({"enabled": "true"}, {"enabled": {"type": "bool_str"}})


class TestEmailValidator:
    """Email field validation."""

    def test_valid_email(self) -> None:
        validate_params({"email": "user@example.com"}, {"email": {"type": "email"}})

    def test_invalid_email(self) -> None:
        with pytest.raises(FieldValidationError, match="valid email"):
            validate_params({"email": "not-an-email"}, {"email": {"type": "email"}})


class TestIpValidator:
    """IP address validation."""

    def test_valid_ipv4(self) -> None:
        validate_params({"target": "10.11.2.10"}, {"target": {"type": "ip"}})

    def test_valid_ipv6(self) -> None:
        validate_params({"target": "::1"}, {"target": {"type": "ip"}})

    def test_invalid_ip(self) -> None:
        with pytest.raises(FieldValidationError, match="valid IP"):
            validate_params({"target": "not-an-ip"}, {"target": {"type": "ip"}})

    def test_invalid_ip_out_of_range(self) -> None:
        with pytest.raises(FieldValidationError, match="valid IP"):
            validate_params({"target": "999.999.999.999"}, {"target": {"type": "ip"}})


class TestCidrValidator:
    """CIDR notation validation."""

    def test_valid_cidr(self) -> None:
        validate_params({"net": "10.0.0.0/24"}, {"net": {"type": "cidr"}})

    def test_invalid_cidr(self) -> None:
        with pytest.raises(FieldValidationError, match="CIDR"):
            validate_params({"net": "bogus"}, {"net": {"type": "cidr"}})


class TestMacValidator:
    """MAC address validation."""

    def test_valid_mac(self) -> None:
        validate_params({"mac": "00:11:22:33:44:55"}, {"mac": {"type": "mac"}})

    def test_invalid_mac(self) -> None:
        with pytest.raises(FieldValidationError, match="MAC"):
            validate_params({"mac": "not-a-mac"}, {"mac": {"type": "mac"}})


class TestPortValidator:
    """Port validation."""

    def test_valid_port(self) -> None:
        validate_params({"port": "443"}, {"port": {"type": "port"}})

    def test_valid_port_range(self) -> None:
        validate_params({"port": "8080:8090"}, {"port": {"type": "port"}})

    def test_valid_port_csv(self) -> None:
        validate_params({"port": "80,443"}, {"port": {"type": "port"}})

    def test_port_out_of_range(self) -> None:
        with pytest.raises(FieldValidationError, match="1-65535"):
            validate_params({"port": "99999"}, {"port": {"type": "port"}})

    def test_port_not_numeric(self) -> None:
        with pytest.raises(FieldValidationError, match="numeric"):
            validate_params({"port": "abc"}, {"port": {"type": "port"}})


class TestColorValidator:
    """Hex color validation (6 digits, no # prefix)."""

    def test_valid_color(self) -> None:
        validate_params({"color": "ff0000"}, {"color": {"type": "color"}})

    def test_invalid_color_with_hash(self) -> None:
        with pytest.raises(FieldValidationError, match="6 hex digits"):
            validate_params({"color": "#ff0000"}, {"color": {"type": "color"}})

    def test_invalid_color_short(self) -> None:
        with pytest.raises(FieldValidationError, match="6 hex digits"):
            validate_params({"color": "fff"}, {"color": {"type": "color"}})


class TestHostnameValidator:
    """Hostname validation."""

    def test_valid_hostname(self) -> None:
        validate_params({"host": "my-server-01"}, {"host": {"type": "hostname"}})

    def test_invalid_hostname(self) -> None:
        with pytest.raises(FieldValidationError, match="valid hostname"):
            validate_params({"host": "has spaces!"}, {"host": {"type": "hostname"}})


class TestRequiredField:
    """Required field validation."""

    def test_missing_required(self) -> None:
        with pytest.raises(FieldValidationError, match="required"):
            validate_params({}, {"name": {"type": "str", "required": True}})

    def test_empty_required(self) -> None:
        with pytest.raises(FieldValidationError, match="required"):
            validate_params({"name": ""}, {"name": {"type": "str", "required": True}})

    def test_optional_missing_ok(self) -> None:
        validate_params({}, {"name": {"type": "str"}})  # no error


class TestFieldValidationErrorAttributes:
    """FieldValidationError carries field, value, and rule."""

    def test_attributes(self) -> None:
        with pytest.raises(FieldValidationError) as exc_info:
            validate_params({"tag": "abc"}, {"tag": {"type": "int"}})

        assert exc_info.value.field == "tag"
        assert exc_info.value.value == "abc"
        assert "integer" in exc_info.value.rule
