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


class TestDictValidator:
    """Dict type validator — nested sub-field validation."""

    def setup_method(self) -> None:
        self.registry = ValidatorRegistry()

    def test_dict_with_valid_sub_fields(self) -> None:
        self.registry.validate_params(
            {"options": {"dns": "10.0.0.1", "router": "10.0.0.1"}},
            {
                "options": {
                    "type": "dict",
                    "fields": {
                        "dns": {"type": "str"},
                        "router": {"type": "str"},
                    },
                }
            },
        )

    def test_dict_missing_optional(self) -> None:
        """Optional dict field missing → no error."""
        self.registry.validate_params({}, {"options": {"type": "dict"}})

    def test_dict_missing_required(self) -> None:
        with pytest.raises(FieldValidationError, match="required"):
            self.registry.validate_params({}, {"options": {"type": "dict", "required": True}})

    def test_dict_not_a_dict(self) -> None:
        with pytest.raises(FieldValidationError, match="must be a dict"):
            self.registry.validate_params({"options": "not_a_dict"}, {"options": {"type": "dict"}})

    def test_dict_sub_field_validation(self) -> None:
        """Sub-field type checking works recursively."""
        with pytest.raises(FieldValidationError, match="must be '0' or '1'"):
            self.registry.validate_params(
                {"options": {"enabled": "yes"}},
                {
                    "options": {
                        "type": "dict",
                        "fields": {"enabled": {"type": "bool_str"}},
                    }
                },
            )

    def test_dict_no_sub_validators(self) -> None:
        """Dict without fields spec — accepts any dict."""
        self.registry.validate_params(
            {"options": {"anything": "goes"}}, {"options": {"type": "dict"}}
        )

    def test_dict_empty_value(self) -> None:
        """Empty string treated as missing for dict."""
        self.registry.validate_params({"options": ""}, {"options": {"type": "dict"}})


class TestFieldValidationErrorAttributes:
    """FieldValidationError carries field, value, and rule."""

    def test_attributes(self) -> None:
        with pytest.raises(FieldValidationError) as exc_info:
            raise FieldValidationError("name", "bad!", "must be alphanumeric")
        err = exc_info.value
        assert err.field == "name"
        assert err.value == "bad!"
        assert err.rule == "must be alphanumeric"


class TestPortOrAlias:
    """Validate port_or_alias type: numeric ports, ranges, aliases."""

    def setup_method(self) -> None:
        self.registry = ValidatorRegistry()
        self.spec = {"port": {"type": "port_or_alias"}}

    def test_single_port_valid(self) -> None:
        self.registry.validate_params({"port": "443"}, self.spec)

    def test_port_range_valid(self) -> None:
        self.registry.validate_params({"port": "80:443"}, self.spec)

    def test_port_comma_rejected(self) -> None:
        """Comma-separated ports rejected — use port alias instead."""
        with pytest.raises(FieldValidationError):
            self.registry.validate_params({"port": "80,443,8080"}, self.spec)

    def test_alias_name_valid(self) -> None:
        self.registry.validate_params({"port": "inttest_web_ports"}, self.spec)

    def test_alias_name_caps_valid(self) -> None:
        self.registry.validate_params({"port": "MyPorts"}, self.spec)

    def test_port_zero_rejected(self) -> None:
        with pytest.raises(FieldValidationError, match="1-65535"):
            self.registry.validate_params({"port": "0"}, self.spec)

    def test_port_too_high_rejected(self) -> None:
        with pytest.raises(FieldValidationError, match="1-65535"):
            self.registry.validate_params({"port": "125657"}, self.spec)

    def test_port_negative_rejected(self) -> None:
        with pytest.raises(FieldValidationError, match="1-65535"):
            self.registry.validate_params({"port": "-1"}, self.spec)

    def test_range_too_high_rejected(self) -> None:
        with pytest.raises(FieldValidationError, match="1-65535"):
            self.registry.validate_params({"port": "80:99999"}, self.spec)

    def test_invalid_string_rejected(self) -> None:
        with pytest.raises(FieldValidationError, match="port.*alias"):
            self.registry.validate_params({"port": "not a port!"}, self.spec)


class TestIpClassification:
    """IP validator with version and scope restrictions."""

    registry = ValidatorRegistry()

    # -- IPv4 vs IPv6 version restriction --

    def test_ipv4_accepted_when_v4_required(self) -> None:
        self.registry.validate_params({"addr": "10.0.0.1"}, {"addr": {"type": "ip", "version": 4}})

    def test_ipv6_rejected_when_v4_required(self) -> None:
        with pytest.raises(FieldValidationError, match="IPv4"):
            self.registry.validate_params(
                {"addr": "fd00::1"}, {"addr": {"type": "ip", "version": 4}}
            )

    def test_ipv6_accepted_when_v6_required(self) -> None:
        self.registry.validate_params({"addr": "fd00::1"}, {"addr": {"type": "ip", "version": 6}})

    def test_ipv4_rejected_when_v6_required(self) -> None:
        with pytest.raises(FieldValidationError, match="IPv6"):
            self.registry.validate_params(
                {"addr": "10.0.0.1"}, {"addr": {"type": "ip", "version": 6}}
            )

    def test_both_versions_accepted_without_restriction(self) -> None:
        self.registry.validate_params({"addr": "10.0.0.1"}, {"addr": {"type": "ip"}})
        self.registry.validate_params({"addr": "fd00::1"}, {"addr": {"type": "ip"}})

    # -- Scope: private/public --

    def test_private_ipv4_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "10.0.0.1"}, {"addr": {"type": "ip", "scope": "private"}}
        )

    def test_public_ipv4_rejected_when_private_required(self) -> None:
        with pytest.raises(FieldValidationError, match="private"):
            self.registry.validate_params(
                {"addr": "8.8.8.8"}, {"addr": {"type": "ip", "scope": "private"}}
            )

    def test_private_ipv6_ula_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "fd00::1"}, {"addr": {"type": "ip", "scope": "private"}}
        )

    def test_public_ipv4_accepted_when_public_required(self) -> None:
        self.registry.validate_params(
            {"addr": "8.8.8.8"}, {"addr": {"type": "ip", "scope": "public"}}
        )

    def test_private_ipv4_rejected_when_public_required(self) -> None:
        with pytest.raises(FieldValidationError, match="public"):
            self.registry.validate_params(
                {"addr": "192.168.1.1"}, {"addr": {"type": "ip", "scope": "public"}}
            )

    # -- Scope: unicast/multicast/loopback/link-local --

    def test_unicast_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "10.0.0.1"}, {"addr": {"type": "ip", "scope": "unicast"}}
        )

    def test_multicast_rejected_when_unicast_required(self) -> None:
        with pytest.raises(FieldValidationError, match="unicast"):
            self.registry.validate_params(
                {"addr": "224.0.0.1"}, {"addr": {"type": "ip", "scope": "unicast"}}
            )

    def test_loopback_rejected_when_unicast_required(self) -> None:
        with pytest.raises(FieldValidationError, match="unicast"):
            self.registry.validate_params(
                {"addr": "127.0.0.1"}, {"addr": {"type": "ip", "scope": "unicast"}}
            )

    def test_multicast_ipv4_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "224.0.0.1"}, {"addr": {"type": "ip", "scope": "multicast"}}
        )

    def test_multicast_ipv6_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "ff02::1"}, {"addr": {"type": "ip", "scope": "multicast"}}
        )

    def test_link_local_ipv4_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "169.254.1.1"}, {"addr": {"type": "ip", "scope": "link_local"}}
        )

    def test_link_local_ipv6_accepted(self) -> None:
        self.registry.validate_params(
            {"addr": "fe80::1"}, {"addr": {"type": "ip", "scope": "link_local"}}
        )

    # -- IP/CIDR notation (VIP uses 10.11.99.1/32) --

    def test_ip_with_cidr_suffix_accepted(self) -> None:
        self.registry.validate_params({"addr": "10.11.99.1/32"}, {"addr": {"type": "ip"}})

    def test_ipv6_with_prefix_accepted(self) -> None:
        self.registry.validate_params({"addr": "fd00::1/128"}, {"addr": {"type": "ip"}})
