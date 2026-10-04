#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Verify pylib _validators against OPNsense API probe schemas.

Compares manager field definitions against the live schema data
captured by probe-api-schemas.sh.

Checks:
    1. Enum values in pylib match API schema enum options
    2. Fields in pylib _validators exist in API schema
    3. Fields in API schema missing from pylib _validators
    4. UpdateOnlyTextField detection (password-like fields)
    5. Dynamic enum detection (interface, gateway — device-state dependent)

    6. With ``--baseline-dir``: what the firmware CHANGED between two probes — fields and
       enum options added or removed per managed entity (the upgrade analysis)

Usage:
    python scripts/verify-validators.py [--schema-dir docs/api/data/26.1.5]
    python scripts/verify-validators.py --schema-dir docs/api/data/26.7.5 \
        --baseline-dir docs/api/data/26.7

Output:
    Per-manager comparison table with OK / MISMATCH / MISSING flags; every gap is named
    (the summary counts alone do not say what to port).
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# Map: schema file label → (manager module path, manager class name)
MANAGER_MAP = {
    "auth-user": ("opnsense.managers.auth.user", "AuthUserManager"),
    "auth-group": ("opnsense.managers.auth.group", "AuthGroupManager"),
    "fw-alias": ("opnsense.managers.firewall.alias", "FwAliasManager"),
    "fw-filter-rule": ("opnsense.managers.firewall.filter", "FwFilterManager"),
    "fw-dnat-rule": ("opnsense.managers.firewall.dnat", "FwDnatManager"),
    "fw-snat-rule": ("opnsense.managers.firewall.source_nat", "FwSourceNatManager"),
    "fw-1to1-rule": ("opnsense.managers.firewall.one_to_one", "FwOneToOneManager"),
    "fw-npt-rule": ("opnsense.managers.firewall.npt", "FwNptManager"),
    "fw-category": ("opnsense.managers.firewall.category", "FwCategoryManager"),
    "fw-group": ("opnsense.managers.firewall.group", "FwGroupManager"),
    "if-vlan": ("opnsense.managers.interfaces.vlan", "IfVlanManager"),
    "if-vip": ("opnsense.managers.interfaces.vip", "IfVipManager"),
    "if-bridge": ("opnsense.managers.interfaces.bridge", "IfBridgeManager"),
    "if-loopback": ("opnsense.managers.interfaces.loopback", "IfLoopbackManager"),
    "if-neighbor": ("opnsense.managers.interfaces.neighbor", "IfNeighborManager"),
    "if-vxlan": ("opnsense.managers.interfaces.vxlan", "IfVxlanManager"),
    "if-gif": ("opnsense.managers.interfaces.gif", "IfGifManager"),
    "if-gre": ("opnsense.managers.interfaces.gre", "IfGreManager"),
    "if-lagg": ("opnsense.managers.interfaces.lagg", "IfLaggManager"),
    "routing-gw": ("opnsense.managers.routing.gateway", "RtGatewayManager"),
    "route": ("opnsense.managers.routing.route", "RtRouteManager"),
    "ub-host-override": ("opnsense.managers.dns.ub_host_override", "UbHostOverrideManager"),
    "ub-forward": ("opnsense.managers.dns.ub_forward", "UbForwardManager"),
    "ub-acl": ("opnsense.managers.dns.ub_acl", "UbAclManager"),
    # UbDotManager uses same schema file as UbForwardManager (ub-forward)
    # but with payload_key="dot". Mapped to ub-forward, override payload_key below.
    "kea4-subnet": ("opnsense.managers.dhcp.kea4_subnet", "Kea4SubnetManager"),
    "kea4-reservation": ("opnsense.managers.dhcp.kea4_reservation", "Kea4ReservationManager"),
    "kea4-peer": ("opnsense.managers.dhcp.kea4_peer", "Kea4PeerManager"),
    "kea6-subnet": ("opnsense.managers.dhcp.kea6_subnet", "Kea6SubnetManager"),
    "kea6-reservation": ("opnsense.managers.dhcp.kea6_reservation", "Kea6ReservationManager"),
    "wg-server": ("opnsense.managers.vpn.wg_server", "WgServerManager"),
    "wg-client": ("opnsense.managers.vpn.wg_client", "WgClientManager"),
    "ipsec-conn": ("opnsense.managers.vpn.ipsec_conn", "IpsecConnManager"),
    "ipsec-child": ("opnsense.managers.vpn.ipsec_child", "IpsecChildManager"),
    "ipsec-local": ("opnsense.managers.vpn.ipsec_local", "IpsecLocalManager"),
    "ipsec-remote": ("opnsense.managers.vpn.ipsec_remote", "IpsecRemoteManager"),
    "ipsec-psk": ("opnsense.managers.vpn.ipsec_psk", "IpsecPskManager"),
    "ipsec-keypair": ("opnsense.managers.vpn.ipsec_keypair", "IpsecKeypairManager"),
    "ipsec-pool": ("opnsense.managers.vpn.ipsec_pool", "IpsecPoolManager"),
    "ipsec-vti": ("opnsense.managers.vpn.ipsec_vti", "IpsecVtiManager"),
    "ovpn-instance": ("opnsense.managers.vpn.ovpn_instance", "OvpnInstanceManager"),
    "ts-pipe": ("opnsense.managers.shaper.ts_pipe", "TsPipeManager"),
    "ts-queue": ("opnsense.managers.shaper.ts_queue", "TsQueueManager"),
    "ts-rule": ("opnsense.managers.shaper.ts_rule", "TsRuleManager"),
    "syslog-dest": ("opnsense.managers.services.syslog_dest", "SyslogDestManager"),
    "cron-job": ("opnsense.managers.services.cron_job", "CronJobManager"),
    "cp-zone": ("opnsense.managers.services.cp_zone", "CpZoneManager"),
    "trust-ca": ("opnsense.managers.trust.ca", "TrustCaManager"),
    "trust-cert": ("opnsense.managers.trust.cert", "TrustCertManager"),
}

# Fields that are device-state dependent (not static enums)
DYNAMIC_FIELDS = {
    "interface",
    "gateway",
    "categories",
    "members",
    "peers",
    "connection",
    "certificate",
    "ca",
    "caref",
    "authservers",
    "group_memberships",
    "priv",
    "language",
    "content",
    "sched",
    "shaper1",
    "shaper2",
    "overload",
    "replyto",
}


# Inputs a manager still accepts but translates before the call (the API never had them, or
# renamed them): not a gap between pylib and the schema.
LEGACY_INPUT_FIELDS = {
    "fw-1to1-rule": {"disabled"},  # API field is `enabled`
    "route": {"disabled"},  # renamed `enabled` on 26.7
}

# Option keys that come from the probed DEVICE, not from the firmware: interface idents and
# devices, certificate refs. A changed option made only of these says the two probes
# ran on different appliances.
DEVICE_OPTION_RE = re.compile(
    r"^(lan|wan|opt\d+|lo\d+|vtnet\d+|vlan\d+|em\d+|igb\d+|ix\d+|[0-9a-f]{13})$"
)
# Enums whose options depend on what is installed or configured on the device.
DEVICE_ENUM_FIELDS = {
    "command",
    "program",
    "authmode",
    "groups",
    "local_group",
    "authEnforceGroup",
}


def classify_schema_field(key: str, value: Any) -> str:
    """Classify a schema field as ENUM_STATIC, ENUM_DYNAMIC, STR, or BCRYPT."""
    if isinstance(value, dict):
        has_selected = any(isinstance(v, dict) and "selected" in v for v in value.values())
        if has_selected:
            if key in DYNAMIC_FIELDS:
                return "ENUM_DYNAMIC"
            return "ENUM_STATIC"
    if isinstance(value, str):
        if value.startswith("$2y$"):
            return "BCRYPT"
        return "STR"
    return type(value).__name__


def get_enum_keys(value: dict) -> list[str]:
    """Extract enum option keys from an OPNsense schema enum dict."""
    return [k for k, v in value.items() if isinstance(v, dict) and "selected" in v]


def load_manager(module_path: str, class_name: str) -> Any:
    """Import and return a manager class (without instantiating)."""
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def unwrap_schema(schema_data: dict[str, Any], payload_key: str) -> dict[str, Any]:
    """Unwrap the payload key (``{"user": {...}}`` → ``{...}``)."""
    if payload_key and payload_key in schema_data:
        return schema_data[payload_key]
    if len(schema_data) == 1:
        return next(iter(schema_data.values()))
    return schema_data


def compare_with_baseline(schema_dir: Path, baseline_dir: Path) -> int:
    """Print what changed between two probes for every managed entity.

    Fields added or removed, and static enum options added or removed. Dynamic enums
    (interfaces, gateways, …) depend on the probed device, not on the firmware, and are
    skipped.

    Returns:
        The number of changes found.
    """
    print(f"\n{'=' * 60}")
    print(f"CHANGES {baseline_dir.name} -> {schema_dir.name} (managed entities)")
    changes = 0
    device_only = 0
    for label, (mod_path, cls_name) in sorted(MANAGER_MAP.items()):
        new_file = schema_dir / f"{label}__schema.json"
        old_file = baseline_dir / f"{label}__schema.json"
        if not new_file.exists() or not old_file.exists():
            if new_file.exists() != old_file.exists():
                side = schema_dir.name if new_file.exists() else baseline_dir.name
                print(f"  {label}: schema only in {side}")
                changes += 1
            continue
        try:
            payload_key = getattr(load_manager(mod_path, cls_name), "_payload_key", "")
        except Exception:
            payload_key = ""
        new = unwrap_schema(json.loads(new_file.read_text()), payload_key)
        old = unwrap_schema(json.loads(old_file.read_text()), payload_key)
        if not isinstance(new, dict) or not isinstance(old, dict):
            continue
        lines = []
        for field in sorted(set(new) - set(old)):
            lines.append(f"    + {field} ({classify_schema_field(field, new[field])})")
        for field in sorted(set(old) - set(new)):
            lines.append(f"    - {field} ({classify_schema_field(field, old[field])})")
        for field in sorted(set(new) & set(old)):
            if (
                classify_schema_field(field, new[field]) == "ENUM_STATIC"
                and classify_schema_field(field, old[field]) == "ENUM_STATIC"
            ):
                added = sorted(set(get_enum_keys(new[field])) - set(get_enum_keys(old[field])))
                removed = sorted(set(get_enum_keys(old[field])) - set(get_enum_keys(new[field])))
                if not (added or removed):
                    continue
                if field in DEVICE_ENUM_FIELDS or all(
                    DEVICE_OPTION_RE.match(opt) for opt in added + removed
                ):
                    device_only += 1  # another appliance, not another firmware
                    continue
                lines.append(f"    ~ {field}: options added {added} removed {removed}")
        if lines:
            print(f"  {label} ({cls_name})")
            print("\n".join(lines))
            changes += len(lines)
    print(f"CHANGES: {changes} (+ {device_only} option lists that differ only by device state)")
    return changes


def main() -> None:
    """Compare pylib validators against the probed API schemas and report gaps."""
    parser = argparse.ArgumentParser(description="Verify pylib validators vs API schemas")
    parser.add_argument("--schema-dir", default="docs/api/data/26.1.5")
    parser.add_argument(
        "--baseline-dir",
        default=None,
        help="an older probe: also report what the firmware changed since then",
    )
    args = parser.parse_args()

    schema_dir = Path(args.schema_dir)
    if not schema_dir.is_dir():
        print(f"Schema dir not found: {schema_dir}")
        sys.exit(1)
    baseline_dir = Path(args.baseline_dir) if args.baseline_dir else None
    if baseline_dir is not None and not baseline_dir.is_dir():
        print(f"Baseline dir not found: {baseline_dir}")
        sys.exit(1)

    total_ok = 0
    total_mismatch = 0
    total_missing_pylib = 0
    total_missing_schema = 0

    for label, (mod_path, cls_name) in sorted(MANAGER_MAP.items()):
        schema_file = schema_dir / f"{label}__schema.json"
        if not schema_file.exists():
            print(f"\n--- {label} --- SCHEMA FILE MISSING: {schema_file}")
            continue

        try:
            mgr_cls = load_manager(mod_path, cls_name)
        except Exception as e:
            print(f"\n--- {label} --- IMPORT ERROR: {e}")
            continue

        validators = getattr(mgr_cls, "_validators", {})
        schema_data = json.loads(schema_file.read_text())

        schema = unwrap_schema(schema_data, getattr(mgr_cls, "_payload_key", ""))

        print(f"\n--- {label} ({cls_name}) ---")

        # Check each pylib validator field against schema
        for field, spec in validators.items():
            vtype = spec.get("type", "str")
            if field not in schema:
                # Check hyphenated variants
                alt = field.replace("_", "-")
                if field in LEGACY_INPUT_FIELDS.get(label, set()):
                    continue  # accepted and translated by the manager
                if alt not in schema and field not in ("state",):
                    print(
                        f"  {field}: NOT IN SCHEMA — pylib validates a field the API does not have"
                    )
                    total_missing_schema += 1
                continue

            schema_val = schema[field]
            schema_type = classify_schema_field(field, schema_val)

            if vtype == "enum" and schema_type == "ENUM_STATIC":
                pylib_values = set(spec.get("values", []))
                api_values = set(get_enum_keys(schema_val))
                if pylib_values == api_values:
                    total_ok += 1
                elif pylib_values.issubset(api_values):
                    missing = api_values - pylib_values
                    print(f"  {field}: ENUM pylib SUBSET — missing {missing}")
                    total_mismatch += 1
                else:
                    extra = pylib_values - api_values
                    print(f"  {field}: ENUM MISMATCH — pylib has {extra} not in API")
                    total_mismatch += 1
            elif vtype == "enum" and schema_type == "ENUM_DYNAMIC":
                total_ok += 1  # dynamic, can't compare static values
            else:
                total_ok += 1

        # Check schema fields missing from pylib
        for field in schema:
            if field == "uuid" or field.startswith("_"):
                continue
            if field not in validators:
                alt = field.replace("-", "_")
                if (
                    alt not in validators
                    and classify_schema_field(field, schema[field]) == "ENUM_STATIC"
                ):
                    options = sorted(get_enum_keys(schema[field]))
                    print(f"  {field}: STATIC ENUM not validated by pylib — {options}")
                    total_missing_pylib += 1

    print(f"\n{'=' * 60}")
    print(
        f"SUMMARY: {total_ok} OK | {total_mismatch} enum mismatches | "
        f"{total_missing_pylib} static enums missing from pylib | "
        f"{total_missing_schema} pylib fields missing from schema"
    )

    if baseline_dir is not None:
        compare_with_baseline(schema_dir, baseline_dir)

    if total_mismatch > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
