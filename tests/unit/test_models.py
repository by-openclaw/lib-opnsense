# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models — typed frozen dataclasses."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from opnsense.models import (
    AuthGroup,
    AuthUser,
    EnsureResult,
    FwAlias,
    FwCategory,
    FwDnatRule,
    FwFilterRule,
    FwGroup,
    FwOneToOneRule,
    FwSourceNatRule,
    IfVip,
    IfVlan,
    TsPipe,
)


class TestFrozenImmutability:
    """All models are frozen — no mutation after construction."""

    @pytest.mark.parametrize(
        "model",
        [
            AuthUser(name="rune"),
            AuthGroup(name="admins"),
            FwAlias(name="trusted"),
            FwFilterRule(description="block all"),
            FwDnatRule(descr="port forward"),
            FwSourceNatRule(description="masquerade"),
            FwOneToOneRule(description="1to1"),
            FwCategory(name="web"),
            FwGroup(ifname="grp0"),
            IfVlan(tag="100"),
            IfVip(address="10.0.0.1"),
            TsPipe(description="upstream"),
            EnsureResult(changed=False, action="noop"),
        ],
    )
    def test_frozen(self, model: object) -> None:
        with pytest.raises(AttributeError):
            model.uuid = "changed"  # type: ignore[attr-defined]


class TestAuthUser:
    """AuthUser model fields and defaults."""

    def test_required_field(self) -> None:
        user = AuthUser(name="svc-test")
        assert user.name == "svc-test"

    def test_defaults(self) -> None:
        user = AuthUser(name="rune")
        assert user.email == ""
        assert user.password == ""
        assert user.disabled == "0"
        assert user.shell == ""
        assert user.expires == ""
        assert user.uuid == ""

    def test_all_fields(self) -> None:
        user = AuthUser(
            name="rune",
            email="rune@example.com",
            password="secret",
            disabled="0",
            shell="/bin/sh",
            expires="2026-12-31",
            uuid="abc-123",
        )
        assert user.email == "rune@example.com"
        assert user.shell == "/bin/sh"
        assert user.uuid == "abc-123"

    def test_asdict(self) -> None:
        user = AuthUser(name="rune")
        d = asdict(user)
        assert d["name"] == "rune"
        assert "uuid" in d


class TestAuthGroup:
    """AuthGroup model fields and defaults."""

    def test_required_field(self) -> None:
        group = AuthGroup(name="admins")
        assert group.name == "admins"

    def test_defaults(self) -> None:
        group = AuthGroup(name="admins")
        assert group.description == ""
        assert group.uuid == ""


class TestFwAlias:
    """FwAlias model fields and defaults."""

    def test_required_field(self) -> None:
        alias = FwAlias(name="trusted_hosts")
        assert alias.name == "trusted_hosts"

    def test_defaults(self) -> None:
        alias = FwAlias(name="test")
        assert alias.type == "host"
        assert alias.enabled == "1"
        assert alias.content == ""


class TestFwFilterRule:
    """FwFilterRule model fields and defaults."""

    def test_required_field(self) -> None:
        rule = FwFilterRule(description="Allow HTTPS")
        assert rule.description == "Allow HTTPS"

    def test_defaults(self) -> None:
        rule = FwFilterRule(description="test")
        assert rule.action == "pass"
        assert rule.direction == "in"
        assert rule.enabled == "1"
        assert rule.quick == "1"
        assert rule.log == "0"

    def test_composite_identity(self) -> None:
        rule = FwFilterRule(
            description="Allow HTTPS",
            interface="lan",
            direction="in",
            protocol="TCP",
        )
        assert rule.interface == "lan"
        assert rule.protocol == "TCP"


class TestFwDnatRule:
    """FwDnatRule model — uses 'descr' not 'description'."""

    def test_descr_field(self) -> None:
        rule = FwDnatRule(descr="port forward 443")
        assert rule.descr == "port forward 443"

    def test_defaults(self) -> None:
        rule = FwDnatRule(descr="test")
        assert rule.disabled == "0"
        assert rule.ipprotocol == "inet"


class TestFwSourceNatRule:
    """FwSourceNatRule model fields."""

    def test_required_field(self) -> None:
        rule = FwSourceNatRule(description="masquerade")
        assert rule.description == "masquerade"

    def test_defaults(self) -> None:
        rule = FwSourceNatRule(description="test")
        assert rule.enabled == "1"
        assert rule.ipprotocol == "inet"


class TestFwOneToOneRule:
    """FwOneToOneRule model fields."""

    def test_required_field(self) -> None:
        rule = FwOneToOneRule(description="1to1 nat")
        assert rule.description == "1to1 nat"

    def test_defaults(self) -> None:
        rule = FwOneToOneRule(description="test")
        assert rule.disabled == "0"


class TestFwCategory:
    """FwCategory model fields."""

    def test_required_field(self) -> None:
        cat = FwCategory(name="web")
        assert cat.name == "web"

    def test_color(self) -> None:
        cat = FwCategory(name="web", color="ff0000")
        assert cat.color == "ff0000"


class TestFwGroup:
    """FwGroup model — uses 'ifname' as identity."""

    def test_required_field(self) -> None:
        grp = FwGroup(ifname="trusted_if")
        assert grp.ifname == "trusted_if"

    def test_defaults(self) -> None:
        grp = FwGroup(ifname="grp0")
        assert grp.members == ""
        assert grp.descr == ""


class TestIfVlan:
    """IfVlan model — composite key (tag + if)."""

    def test_required_field(self) -> None:
        vlan = IfVlan(tag="100")
        assert vlan.tag == "100"

    def test_defaults(self) -> None:
        vlan = IfVlan(tag="100")
        assert vlan.if_ == ""
        assert vlan.pcp == ""
        assert vlan.descr == ""


class TestIfVip:
    """IfVip model — CARP password is a field."""

    def test_required_field(self) -> None:
        vip = IfVip(address="10.0.0.1")
        assert vip.address == "10.0.0.1"

    def test_defaults(self) -> None:
        vip = IfVip(address="10.0.0.1")
        assert vip.mode == "ipalias"
        assert vip.password == ""

    def test_carp_mode(self) -> None:
        vip = IfVip(address="10.0.0.1", mode="carp", password="secret")
        assert vip.mode == "carp"
        assert vip.password == "secret"


class TestTsPipe:
    """TsPipe model fields."""

    def test_required_field(self) -> None:
        pipe = TsPipe(description="upstream")
        assert pipe.description == "upstream"

    def test_defaults(self) -> None:
        pipe = TsPipe(description="test")
        assert pipe.bandwidthMetric == "Mbit"
        assert pipe.enabled == "1"

    def test_bandwidth(self) -> None:
        pipe = TsPipe(description="100mbit", bandwidth="100", bandwidthMetric="Mbit")
        assert pipe.bandwidth == "100"


class TestEnsureResult:
    """EnsureResult base model."""

    def test_noop(self) -> None:
        r = EnsureResult(changed=False, action="noop")
        assert r.changed is False
        assert r.uuid is None
        assert r.before is None
        assert r.after is None

    def test_created(self) -> None:
        r = EnsureResult(changed=True, action="created", uuid="abc", after={"name": "rune"})
        assert r.changed is True
        assert r.uuid == "abc"
        assert r.after == {"name": "rune"}
