# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense

# API Coverage — lib-opnsense

> Probed against OPNsense **26.1.5** — 200/200 endpoints OK.
> Probe data: `docs/api/data/26.1.5/`
> Last updated: 2026-04-11

## Status Legend

| Status | Meaning |
|---|---|
| `INTEGRATION_TEST_PASSED` | Manager + unit tests + integration tests on live device |
| `UNIT_TEST_PASSED` | Manager + unit tests, no integration test yet |
| `PARTIAL` | Manager code exists, tests incomplete |
| `ABSENT` | No manager code yet |
| `SKIPPED` | Intentionally not implemented — replaced by other service or not needed on firewall |
| `NOT_AVAILABLE` | API broken or missing on this firmware version |

## Summary

| Metric | Count |
|---|---|
| Total API domains probed | 134 |
| CRUD domains (schema + search) | 66 |
| Read-only / service / settings domains | 68 |
| **Total managers needed** | **134** |
| Managers done (integration tested) | 54 |
| Integration test files | 49 (~360 tests across 10 scopes) |
| Unit tests | 1,207 |
| Managers done (unit tested only) | 0 |
| Managers partial | 0 |
| Managers absent (CRUD) | 48 |
| Managers absent (read-only) | 68 |

---

## Auth (4 managers — changes apply immediately)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| auth-user | `AuthUserManager` | `name` | `auth/user` | `INTEGRATION_TEST_PASSED` | Redacts password, otp, SSH keys |
| auth-group | `AuthGroupManager` | `name` | `auth/group` | `INTEGRATION_TEST_PASSED` | Server rejects duplicate names |
| auth-priv | `AuthPrivManager` | — | `auth/priv` | `INTEGRATION_TEST_PASSED` | Standalone, privilege assignment |
| auth-apikey | `AuthApiKeyManager` | — | `auth/user/search_api_key` | `INTEGRATION_TEST_PASSED` | Standalone, API key lifecycle |

## Firewall (8 managers — requires apply/reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| fw-alias | `FwAliasManager` | `name` | `firewall/alias` | `INTEGRATION_TEST_PASSED` | Host, network, port, URL aliases |
| fw-filter | `FwFilterManager` | `description, interface, direction, protocol` | `firewall/filter` | `INTEGRATION_TEST_PASSED` | Pass/block/reject rules, duplicates allowed |
| fw-dnat | `FwDnatManager` | `descr, interface, target` | `firewall/d_nat` | `INTEGRATION_TEST_PASSED` | Port forwarding, duplicates allowed |
| fw-snat | `FwSourceNatManager` | `description, interface, source_net` | `firewall/source_nat` | `INTEGRATION_TEST_PASSED` | Outbound NAT / masquerade |
| fw-1to1 | `FwOneToOneManager` | `description, interface, source_net` | `firewall/one_to_one` | `INTEGRATION_TEST_PASSED` | Bidirectional 1:1 NAT |
| fw-category | `FwCategoryManager` | `name` | `firewall/category` | `INTEGRATION_TEST_PASSED` | Rule categories (immediate) |
| fw-group | `FwGroupManager` | `ifname` | `firewall/group` | `INTEGRATION_TEST_PASSED` | Interface groups (immediate) |
| fw-npt | `FwNptManager` | `source_net, destination_net` | `firewall/npt` Rule | `INTEGRATION_TEST_PASSED` | IPv6 NPTv6 (NAT66), disabled ULA prefixes for testing |

## Interfaces (9 managers — requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| if-vlan | `IfVlanManager` | `tag, if` | `interfaces/vlan_settings` | `INTEGRATION_TEST_PASSED` | 802.1Q VLAN sub-interfaces |
| if-vip | `IfVipManager` | `address, interface, mode` | `interfaces/vip_settings` | `INTEGRATION_TEST_PASSED` | IP alias, CARP, proxy ARP |
| if-bridge | `IfBridgeManager` | `descr` | `interfaces/bridge_settings` | `INTEGRATION_TEST_PASSED` | Needs physical members, unit tested only |
| if-gif | `IfGifManager` | `tunnel-local-addr, tunnel-remote-addr` | `interfaces/gif_settings` | `INTEGRATION_TEST_PASSED` | GIF tunnels, unit tested only |
| if-gre | `IfGreManager` | `tunnel-local-addr, tunnel-remote-addr` | `interfaces/gre_settings` | `INTEGRATION_TEST_PASSED` | GRE tunnels, unit tested only |
| if-lagg | `IfLaggManager` | `descr` | `interfaces/lagg_settings` | `INTEGRATION_TEST_PASSED` | Link aggregation, unit tested only |
| if-loopback | `IfLoopbackManager` | `description` | `interfaces/loopback_settings` | `INTEGRATION_TEST_PASSED` | Loopback interfaces |
| if-neighbor | `IfNeighborManager` | `ipaddress, etheraddr` | `interfaces/neighbor_settings` | `INTEGRATION_TEST_PASSED` | Static ARP entries |
| if-vxlan | `IfVxlanManager` | `vxlanid, vxlanlocal` | `interfaces/vxlan_settings` | `INTEGRATION_TEST_PASSED` | VXLAN tunnels |

## Routing (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| routing-gw | `RtGatewayManager` | `name` | `routing/settings` Gateway | `INTEGRATION_TEST_PASSED` | API supports full CRUD. Tests are read-only — full CRUD deferred to WireGuard (2.14) when a real test gateway exists |
| route | `RtRouteManager` | `network, gateway` | `routes/routes` Route | `INTEGRATION_TEST_PASSED` | CRUD with disabled=1, Null4 blackhole gateway (127.0.0.1, drops traffic), inttest- prefix |

## Unbound DNS (6 managers — requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| ub-host-override | `UbHostOverrideManager` | `hostname, domain, server` | `unbound/settings` HostOverride | `INTEGRATION_TEST_PASSED` | Local A/AAAA/MX/TXT records, full CRUD |
| ub-host-alias | `UbHostAliasManager` | `hostname, domain` | `unbound/settings` HostAlias | `INTEGRATION_TEST_PASSED` | Create+read only (set/del=404 on 26.1.5) |
| ub-forward | `UbForwardManager` | `domain, server` | `unbound/settings` Forward | `INTEGRATION_TEST_PASSED` | Domain-specific DNS forwarding |
| ub-acl | `UbAclManager` | `name` | `unbound/settings` Acl | `INTEGRATION_TEST_PASSED` | Resolver access control lists |
| ub-dot | `UbDotManager` | `server, port` | `unbound/settings` Dot | `INTEGRATION_TEST_PASSED` | DNS-over-TLS upstream servers |
| ub-dnsbl | `UbDiagnosticsManager` | — | `unbound/settings` getDnsbl | `INTEGRATION_TEST_PASSED` | Read-only (add/set/del=404 on 26.1.5) |
| ub-diag-stats | `UbDiagnosticsManager` | — | `unbound/diagnostics/stats` | `INTEGRATION_TEST_PASSED` | Read-only resolver statistics |
| ub-domain-override | — | — | API broken on 26.1.5 | `NOT_AVAILABLE` | Empty response from server |

## Kea DHCPv4 (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| kea4-subnet | `Kea4SubnetManager` | `subnet` | `kea/dhcpv4` Subnet | `INTEGRATION_TEST_PASSED` | Full CRUD, test subnet 10.99.0.0/24 |
| kea4-reservation | `Kea4ReservationManager` | `ip_address, hw_address` | `kea/dhcpv4` Reservation | `INTEGRATION_TEST_PASSED` | Requires parent subnet UUID in 'subnet' field |
| kea4-peer | `Kea4PeerManager` | `name` | `kea/dhcpv4` Peer | `INTEGRATION_TEST_PASSED` | HA peer (primary/standby) |

## Kea DHCPv6 (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| kea6-subnet | `Kea6SubnetManager` | `subnet` | `kea/dhcpv6` Subnet | `INTEGRATION_TEST_PASSED` | Requires `interface` field (mandatory). Kea DHCPv6 enabled on LAN |
| kea6-reservation | `Kea6ReservationManager` | `ip_address, duid` | `kea/dhcpv6` Reservation | `INTEGRATION_TEST_PASSED` | Requires parent subnet UUID in 'subnet' field |

## WireGuard (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| wg-server | `WgServerManager` | `name` | `wireguard/server` Server | `INTEGRATION_TEST_PASSED` | Tunnel interface. generate_keypair() creates key pair. privkey required. Redacts privkey/pubkey. Store privkey in Vault KV |
| wg-client | `WgClientManager` | `name` | `wireguard/client` Client | `INTEGRATION_TEST_PASSED` | Peer entry. Needs remote device's pubkey (client generates own keys). Redacts psk/pubkey |
| wg-keypair | `WgServerManager.generate_keypair()` | — | `wireguard/server/keyPair` | `INTEGRATION_TEST_PASSED` | Returns {privkey, pubkey}. Server-side only. Client generates keys on their device |

## IPsec (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| ipsec-conn | `IpsecConnManager` | `description` | `ipsec/connections` Connection | `INTEGRATION_TEST_PASSED` | IKE connection. Child/Local/Remote reference by UUID |
| ipsec-child | `IpsecChildManager` | `description` | `ipsec/connections` Child | `INTEGRATION_TEST_PASSED` | SA child. Needs parent connection UUID |
| ipsec-local | `IpsecLocalManager` | `description` | `ipsec/connections` Local | `INTEGRATION_TEST_PASSED` | Local auth. Needs parent connection UUID |
| ipsec-remote | `IpsecRemoteManager` | `description` | `ipsec/connections` Remote | `INTEGRATION_TEST_PASSED` | Remote auth. Needs parent connection UUID |
| ipsec-psk | `IpsecPskManager` | `description` | `ipsec/pre_shared_keys` Item | `INTEGRATION_TEST_PASSED` | Pre-shared keys. Redacts Key |
| ipsec-keypair | `IpsecKeypairManager` | `name` | `ipsec/key_pairs` Item | `INTEGRATION_TEST_PASSED` | Key pairs. Redacts privateKey |
| ipsec-pool | `IpsecPoolManager` | `name` | `ipsec/pools` (bare) | `INTEGRATION_TEST_PASSED` | IP address pools for clients |
| ipsec-vti | `IpsecVtiManager` | `description` | `ipsec/vti` (bare) | `INTEGRATION_TEST_PASSED` | Virtual tunnel interfaces. reqid + tunnel IPs required (plain, no CIDR) |

## Traffic Shaper (3 managers — requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| ts-pipe | `TsPipeManager` | `description, bandwidth, bandwidthMetric` | `trafficshaper/settings` Pipe | `INTEGRATION_TEST_PASSED` | Bandwidth pipes |
| ts-queue | `TsQueueManager` | `description` | `trafficshaper/settings` Queue | `INTEGRATION_TEST_PASSED` | Requires parent pipe UUID in 'pipe' field. Plural search (searchQueues) |
| ts-rule | `TsRuleManager` | `description, interface, proto` | `trafficshaper/settings` Rule | `INTEGRATION_TEST_PASSED` | Requires target pipe/queue UUID in 'target' field. Plural search (searchRules) |

## Syslog (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| syslog-dest | `SyslogDestManager` | `description` | `syslog/settings` Destination | `INTEGRATION_TEST_PASSED` | Remote syslog target. Plural search (searchDestinations). Created disabled for testing |

## Cron (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| cron-job | `CronJobManager` | `description` | `cron/settings` Job | `INTEGRATION_TEST_PASSED` | Plural search (searchJobs). Scheduled tasks |

## DynDNS (requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| ddns-account | `DdnsAccountManager` | `description` | `dyndns/accounts` Item | `INTEGRATION_TEST_PASSED` | Built-in on 26.1 (not os-ddclient). Supports Cloudflare, AWS, etc. Redacts password. hostnames + checkip required |

## Trust / PKI

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| trust-ca | `TrustCaManager` | `descr` | `trust/ca` (bare) | `INTEGRATION_TEST_PASSED` | Internal generate or import PEM. Redacts prv/prv_payload. Cert caref uses refid not UUID |
| trust-cert | `TrustCertManager` | `descr` | `trust/cert` (bare) | `INTEGRATION_TEST_PASSED` | Needs CA refid in caref. Import or generate. Redacts prv/prv_payload/csr_payload |

## IDS / Suricata

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| ids-policy | `IdsPolicyManager` | `GET /api/ids/settings/get_policy`, `POST /api/ids/settings/search_policy` | `ABSENT` |
| ids-policy-rule | `IdsPolicyRuleManager` | `GET /api/ids/settings/get_policy_rule`, `POST /api/ids/settings/search_policy_rule` | `ABSENT` |
| ids-user-rule | `IdsUserRuleManager` | `GET /api/ids/settings/get_user_rule`, `POST /api/ids/settings/search_user_rule` | `ABSENT` |

## Captive Portal

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| cp-zone | `CpZoneManager` | `description` | `captiveportal/settings` Zone | `INTEGRATION_TEST_PASSED` | Guest portal zones. Plural search (searchZones). Created disabled for testing |

## OpenVPN

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| ovpn-instance | `OvpnInstanceManager` | `description` | `openvpn/instances` (bare) | `INTEGRATION_TEST_PASSED` | Server or client mode. Needs CA + cert refids. vpnid required. Redacts password |
| ovpn-cso | — | — | — | `NOT_AVAILABLE` | CSO endpoints 404 on 26.1.5 — not a separate entity |

## DHCP Relay

| Domain | Manager | Endpoints | Status | Notes |
|---|---|---|---|---|
| dhcrelay-dest | — | `dhcrelay/settings` | `SKIPPED` | Not needed — Kea serves directly on all VLANs, no relay required |
| dhcrelay-relay | — | `dhcrelay/settings` | `SKIPPED` | Only needed when DHCP server is on a different machine |

## Plugin Management

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| plugins | `PluginManager` | — | `core/firmware` | `INTEGRATION_TEST_PASSED` | List/install/remove plugins. Not BaseManager — custom methods |

## Monit

| Domain | Manager | Endpoints | Status | Notes |
|---|---|---|---|---|
| monit-* (3 domains) | — | `monit/settings` | `SKIPPED` | Use Prometheus + node_exporter instead for monitoring |

## Dnsmasq

| Domain | Manager | Endpoints | Status | Notes |
|---|---|---|---|---|
| dnsmasq-* (6 domains) | — | `dnsmasq/settings` | `PENDING` | OPNsense 26.1 default for DHCP4+DHCP6+RA. Managers tracked under epic [#65](https://github.com/by-openclaw/lib-opnsense/issues/65). Was `SKIPPED` ("Replaced by Kea + Unbound") before 26.1 flipped the default — needs full coverage |
| radvd-* (2 domains) | — | `radvd/settings`, `radvd/service` | `PENDING` | Required when running Kea (no built-in RA) or for dynamic IPv6 clients. Epic [#65](https://github.com/by-openclaw/lib-opnsense/issues/65) |

### Base patterns unlocked by epic #65 (foundation for ~30 ABSENT singleton/service managers)

| Component | Status | Notes |
|---|---|---|
| `core/base_singleton.py` — `BaseSingletonManager` | `IMPLEMENTED` | Fetch/diff/set pattern for singleton config objects (`settings/get` + `settings/set`). Needed for dnsmasq, radvd, ids, syslog, routing, wg-general, kea*-global, ub-settings, monit, trust, ts, cron, dhcrelay, etc. |
| `core/base_service.py` — `BaseServiceManager` | `IMPLEMENTED` | Idempotent service control (`service/{status,start,stop,restart,reconfigure}`). Needed for dnsmasq-service, radvd-service, kea-service, ub-service, ids-service, wg-service, ipsec-service, syslog-service, cp-service |

## Core / System

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| core-tunable | `CoreTunableManager` | `GET /api/core/tunables/get_item`, `POST /api/core/tunables/search_item` | `ABSENT` |

---

## Chrony NTP (plugin: os-chrony)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| chrony-general | `ChronoSettingsManager` | `GET /api/chrony/general/get` | `ABSENT` |
| chrony-service | `ChronoServiceManager` | `GET /api/chrony/service/status` | `ABSENT` |

## LLDP (plugin: os-lldpd)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| lldpd-general | `LldpdSettingsManager` | `GET /api/lldpd/general/get` | `ABSENT` |
| lldpd-service | `LldpdServiceManager` | `GET /api/lldpd/service/status` | `ABSENT` |

## Core / Firmware / System

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| core-backup-providers | `CoreBackupManager` | `GET /api/core/backup/providers` | `ABSENT` |
| core-firmware-info | `CoreFirmwareManager` | `GET /api/core/firmware/info` | `ABSENT` |
| core-firmware-running | `CoreFirmwareManager` | `GET /api/core/firmware/running` | `ABSENT` |
| core-firmware-status | `CoreFirmwareManager` | `GET /api/core/firmware/status` | `ABSENT` |
| core-hasync | `CoreHasyncManager` | `GET /api/core/hasync/get` | `ABSENT` |
| core-services | `CoreServiceManager` | `GET /api/core/service/search` | `ABSENT` |
| core-snapshots | `CoreSnapshotManager` | `POST /api/core/snapshots/search` | `ABSENT` |
| core-system | `CoreSystemManager` | `GET /api/core/system/status` | `ABSENT` |
| core-tunables | `CoreTunablesSettingsManager` | `GET /api/core/tunables/get` | `ABSENT` |
| core-zfs-supported | `CoreZfsManager` | `GET /api/core/snapshots/is_supported` | `ABSENT` |

## Diagnostics (read-only)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| diag-arp | `DiagArpManager` | `GET /api/diagnostics/interface/get_arp` | `ABSENT` |
| diag-disk | `DiagDiskManager` | `GET /api/diagnostics/system/system_disk` | `ABSENT` |
| diag-fw-ruleids | `DiagFwRuleIdsManager` | `GET /api/diagnostics/firewall/list_rule_ids` | `ABSENT` |
| diag-fw-stats | `DiagFwStatsManager` | `GET /api/diagnostics/firewall/stats` | `ABSENT` |
| diag-ifconfig | `DiagIfConfigManager` | `GET /api/diagnostics/interface/get_interface_config` | `ABSENT` |
| diag-ifnames | `DiagIfNamesManager` | `GET /api/diagnostics/interface/get_interface_names` | `ABSENT` |
| diag-ifstats | `DiagIfStatsManager` | `GET /api/diagnostics/interface/get_interface_statistics` | `ABSENT` |
| diag-memory | `DiagMemoryManager` | `GET /api/diagnostics/system/memory` | `ABSENT` |
| diag-ndp | `DiagNdpManager` | `GET /api/diagnostics/interface/get_ndp` | `ABSENT` |
| diag-netflow-enabled | `DiagNetflowManager` | `GET /api/diagnostics/netflow/is_enabled` | `ABSENT` |
| diag-netflow-status | `DiagNetflowManager` | `GET /api/diagnostics/netflow/status` | `ABSENT` |
| diag-proto | `DiagProtoManager` | `GET /api/diagnostics/interface/get_protocol_statistics` | `ABSENT` |
| diag-resources | `DiagResourcesManager` | `GET /api/diagnostics/system/system_resources` | `ABSENT` |
| diag-routes | `DiagRoutesManager` | `GET /api/diagnostics/interface/get_routes` | `ABSENT` |
| diag-sysinfo | `DiagSysInfoManager` | `GET /api/diagnostics/system/system_information` | `ABSENT` |
| diag-temp | `DiagTempManager` | `GET /api/diagnostics/system/system_temperature` | `ABSENT` |
| diag-time | `DiagTimeManager` | `GET /api/diagnostics/system/system_time` | `ABSENT` |
| diag-vip | `DiagVipManager` | `GET /api/diagnostics/interface/get_vip_status` | `ABSENT` |

## Service Status (read-only)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| cp-service | `CpServiceManager` | `GET /api/captiveportal/service/status` | `ABSENT` |
| dnsmasq-service | `DnsmasqServiceManager` | `GET /api/dnsmasq/service/status` | `ABSENT` |
| ids-service | `IdsServiceManager` | `GET /api/ids/service/status` | `ABSENT` |
| ipsec-service | `IpsecServiceManager` | `GET /api/ipsec/service/status` | `ABSENT` |
| kea-service | `KeaServiceManager` | `GET /api/kea/service/status` | `ABSENT` |
| syslog-service | `SyslogServiceManager` | `GET /api/syslog/service/status` | `ABSENT` |
| ub-service | `UbServiceManager` | `GET /api/unbound/service/status` | `ABSENT` |
| wg-service | `WgServiceManager` | `GET /api/wireguard/service/status` | `ABSENT` |

## Global Settings (read-only)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| cron-settings | `CronSettingsManager` | `GET /api/cron/settings/get` | `ABSENT` |
| dhcrelay-settings | `DhcrelaySettingsManager` | `GET /api/dhcrelay/settings/get` | `ABSENT` |
| dnsmasq-settings | `DnsmasqSettingsManager` | `GET /api/dnsmasq/settings/get` | `ABSENT` |
| ids-settings | `IdsSettingsManager` | `GET /api/ids/settings/get` | `ABSENT` |
| if-overview | `IfOverviewManager` | `GET /api/interfaces/overview/export` | `ABSENT` |
| if-settings | `IfSettingsManager` | `GET /api/interfaces/settings/get` | `ABSENT` |
| ipsec-enabled | `IpsecEnabledManager` | `GET /api/ipsec/sessions/is_enabled` | `ABSENT` |
| ipsec-settings | `IpsecSettingsManager` | `GET /api/ipsec/connections/get` | `ABSENT` |
| kea-ctrl-agent | `KeaCtrlAgentManager` | `GET /api/kea/ctrl_agent/get` | `ABSENT` |
| kea4-global | `Kea4GlobalManager` | `GET /api/kea/dhcpv4/get` | `ABSENT` |
| kea6-global | `Kea6GlobalManager` | `GET /api/kea/dhcpv6/get` | `ABSENT` |
| monit-settings | `MonitSettingsManager` | `GET /api/monit/settings/get` | `ABSENT` |
| routing-settings | `RoutingSettingsManager` | `GET /api/routing/settings/get` | `ABSENT` |
| syslog-settings | `SyslogSettingsManager` | `GET /api/syslog/settings/get` | `ABSENT` |
| trust-settings | `TrustSettingsManager` | `GET /api/trust/settings/get` | `ABSENT` |
| ts-settings | `TsSettingsManager` | `GET /api/trafficshaper/settings/get` | `ABSENT` |
| ub-settings | `UbSettingsManager` | `GET /api/unbound/settings/get` | `ABSENT` |
| wg-general | `WgGeneralManager` | `GET /api/wireguard/general/get` | `ABSENT` |

## Other Read-only

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| cp-session-zones | `CpSessionManager` | `GET /api/captiveportal/session/zones` | `ABSENT` |
| gw-status | `GwStatusManager` | `GET /api/routes/gateway/status` | `ABSENT` |
| monit-svc-status | `MonitStatusManager` | `GET /api/monit/status/get` | `ABSENT` |
| ovpn-routes | `OvpnExportManager` | `GET /api/openvpn/export/providers` | `ABSENT` |
| ovpn-sessions | `OvpnSessionManager` | `GET /api/openvpn/sessions/search` | `ABSENT` |
| trust-crl | `TrustCrlManager` | `GET /api/trust/crl/search` | `ABSENT` |
| ts-stats | `TsStatsManager` | `GET /api/trafficshaper/service/statistics` | `ABSENT` |
| ub-diag-stats | `UbDiagnosticsManager` | `GET /api/unbound/diagnostics/stats` | `INTEGRATION_TEST_PASSED` |
| wg-show | `WgShowManager` | `GET /api/wireguard/service/show` | `ABSENT` ||
