# Enum Field Reference — lib-opnsense

> **Purpose:** Document which fields use static vs dynamic enums.
> Dynamic enums change based on device state (e.g., creating a VLAN adds it to the interface list).
> Static enums are fixed by OPNsense firmware version.

## Static enums (fixed values per firmware version)

These values are defined in OPNsense MVC models and do not change based on device configuration.
Pylib validates them client-side with `"type": "enum", "values": [...]`.

| Manager | Field | Values (26.1.5) |
|---|---|---|
| FwFilterManager | `action` | pass, block, reject |
| FwFilterManager | `direction` | in, out, any |
| FwFilterManager | `ipprotocol` | inet, inet6, inet46 |
| FwFilterManager | `statetype` | keep, sloppy, modulate, synproxy, none |
| FwDnatManager | `ipprotocol` | "", inet, inet6, inet46 |
| FwDnatManager | `natreflection` | "", purenat, disable |
| FwSourceNatManager | `ipprotocol` | inet, inet6 |
| FwOneToOneManager | `type` | binat, nat |
| FwOneToOneManager | `natreflection` | "", enable, disable |
| IfVlanManager | `proto` | "", 802.1q, 802.1ad |
| IfVipManager | `mode` | ipalias, carp, proxyarp |
| IfLaggManager | `proto` | none, lacp, failover, fec, loadbalance |
| RtGatewayManager | `ipprotocol` | inet, inet6 |
| UbHostOverrideManager | `rr` | A, AAAA, MX, TXT |
| UbAclManager | `action` | allow, deny, refuse, allow_snoop, deny_non_local, refuse_non_local |
| UbForwardManager | `type` | forward, stub |
| UbDotManager | `type` | dot |
| Kea4PeerManager | `role` | primary, standby |
| SyslogDestManager | `transport` | udp4, tcp4, udp6, tcp6 |
| TsPipeManager | `bandwidthMetric` | bit, Kbit, Mbit, Gbit |
| TsPipeManager | `mask` | none, src-ip, dst-ip, src-ip6, dst-ip6 |
| TsPipeManager | `scheduler` | "", fifo, rr, qfq, fq_codel, fq_pie |
| TsRuleManager | `proto` | ip, ip4, ip6, udp, tcp |
| TsRuleManager | `direction` | "", in, out |
| TrustCaManager | `action` | existing, internal |
| TrustCertManager | `action` | internal, external, existing |
| TrustCertManager | `cert_type` | usr_cert, server_cert |
| OvpnInstanceManager | `role` | server, client |

## Dynamic enums (change based on device state)

These values depend on what is configured on the OPNsense device.
Creating a VLAN, bridge, PPPoE, or WireGuard tunnel adds new entries.
Pylib uses `"type": "str"` for these fields — NO client-side enum validation.

| Field | Where it appears | What populates it |
|---|---|---|
| `interface` | FwFilter, FwDnat, FwSnat, Fw1to1, FwNpt, IfVip, TsRule, RtGateway, SyslogDest, CpZone | Physical NICs (vtnet0, vtnet1), VLANs, bridges, LAGG, loopbacks, GIF, GRE, VXLAN, PPPoE, WireGuard tunnel interfaces |
| `gateway` | FwFilter, RtRoute | Configured gateways (WAN_DHCP, WAN_DHCP6, Null4, Null6) + user-created gateways |
| `categories` | FwFilter, FwAlias, FwDnat, FwSnat, Fw1to1, FwNpt | User-created firewall categories (FwCategoryManager) |
| `members` | FwGroupManager, IfBridgeManager, IfLaggManager | Available interfaces (dynamic) |
| `peers` | WgServerManager | WireGuard clients (WgClientManager) |
| `connection` | IpsecChild, IpsecLocal, IpsecRemote | IPsec connections (IpsecConnManager) |
| `certificate` | CpZoneManager, OvpnInstanceManager | Trust certificates (TrustCertManager) |
| `ca` / `caref` | TrustCertManager, OvpnInstanceManager | Certificate authorities (TrustCaManager) |
| `authservers` | CpZoneManager | Authentication servers configured in System > Access > Servers |

## Example: creating a VLAN grows the interface list

```python
# Before: interface enum = {lan, wan}
await vlan_mgr.ensure("present", {"tag": "100", "if": "vtnet0", "descr": "MGMT"})
# After: interface enum = {lan, wan, vlan01}

# Now the new VLAN can be used in firewall rules:
await filter_mgr.ensure("present", {
    "description": "allow-mgmt",
    "interface": "vlan01",  # new dynamic value
    ...
})
```

## Why ansible modules must NOT use `choices:` for dynamic fields

Ansible `argument_spec` with `choices: [wan, lan]` would reject `vlan01` because
it wasn't in the list at module definition time. Dynamic fields must use
`type: str` (no `choices:`) in both pylib validators and ansible modules.

Only static enums (like `action: pass/block/reject`) should have `choices:`.

## Verification

Run the probe script to capture current device enum state:
```bash
cd lib-opnsense
./scripts/probe-api-schemas.sh
```

Compare schemas in `docs/api/data/{version}/` to see how enums grow over time.
