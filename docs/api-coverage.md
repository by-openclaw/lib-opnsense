# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense

# API Coverage — lib-opnsense

> Probed against OPNsense **26.1.5** — 200/200 endpoints OK.
> Probe data: `docs/api/data/26.1.5/`
> Last updated: 2026-04-08

## Status Legend

| Status | Meaning |
|---|---|
| `INTEGRATION_TEST_PASSED` | Manager + unit tests + integration tests on live device |
| `UNIT_TEST_PASSED` | Manager + unit tests, no integration test yet |
| `PARTIAL` | Manager code exists, tests incomplete |
| `ABSENT` | No manager code yet |

## Summary

| Metric | Count |
|---|---|
| Total API domains probed | 134 |
| CRUD domains (schema + search) | 66 |
| Read-only / service / settings domains | 68 |
| **Total managers needed** | **134** |
| Managers done (integration tested) | 25 |
| Managers done (unit tested) | 0 |
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

## Firewall (7 managers — requires apply/reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| fw-alias | `FwAliasManager` | `name` | `firewall/alias` | `INTEGRATION_TEST_PASSED` | Host, network, port, URL aliases |
| fw-filter | `FwFilterManager` | `description, interface, direction, protocol` | `firewall/filter` | `INTEGRATION_TEST_PASSED` | Pass/block/reject rules, duplicates allowed |
| fw-dnat | `FwDnatManager` | `descr, interface, target` | `firewall/d_nat` | `INTEGRATION_TEST_PASSED` | Port forwarding, duplicates allowed |
| fw-snat | `FwSourceNatManager` | `description, interface, source_net` | `firewall/source_nat` | `INTEGRATION_TEST_PASSED` | Outbound NAT / masquerade |
| fw-1to1 | `FwOneToOneManager` | `description, interface, source_net` | `firewall/one_to_one` | `INTEGRATION_TEST_PASSED` | Bidirectional 1:1 NAT |
| fw-category | `FwCategoryManager` | `name` | `firewall/category` | `INTEGRATION_TEST_PASSED` | Rule categories (immediate) |
| fw-group | `FwGroupManager` | `ifname` | `firewall/group` | `INTEGRATION_TEST_PASSED` | Interface groups (immediate) |
| fw-npt | `FwNptManager` | — | `firewall/npt` | `ABSENT` | IPv6 NPTv6 |

## Interfaces (2 managers — requires reconfigure)

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
| ub-host-override | `UbHostOverrideManager` | `hostname, domain, server` | `unbound/settings` HostOverride | `INTEGRATION_TEST_PASSED` | Local A/AAAA/MX records |
| ub-host-alias | `UbHostAliasManager` | `hostname, domain` | `unbound/settings` HostAlias | `INTEGRATION_TEST_PASSED` | Create+read only (set/del=404 on 26.1.5) |
| ub-forward | `UbForwardManager` | `domain, server` | `unbound/settings` Forward | `INTEGRATION_TEST_PASSED` | Domain-specific DNS forwarding |
| ub-acl | `UbAclManager` | `name` | `unbound/settings` Acl | `INTEGRATION_TEST_PASSED` | Resolver access control lists |
| ub-dot | `UbDotManager` | `server, port` | `unbound/settings` Dot | `INTEGRATION_TEST_PASSED` | DNS-over-TLS upstream servers |
| ub-dnsbl | `UbDiagnosticsManager` | — | `unbound/settings` getDnsbl | `INTEGRATION_TEST_PASSED` | Read-only (add/set/del=404 on 26.1.5) |
| ub-diag-stats | `UbDiagnosticsManager` | — | `unbound/diagnostics/stats` | `INTEGRATION_TEST_PASSED` | Read-only resolver statistics |
| ub-domain-override | — | — | API broken on 26.1.5 | `NOT_AVAILABLE` | Empty response from server |

## Kea DHCPv4 (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| kea4-subnet | `Kea4SubnetManager` | `GET /api/kea/dhcpv4/get_subnet`, `POST /api/kea/dhcpv4/search_subnet` | `ABSENT` |
| kea4-reservation | `Kea4ReservationManager` | `GET /api/kea/dhcpv4/get_reservation`, `POST /api/kea/dhcpv4/search_reservation` | `ABSENT` |
| kea4-peer | `Kea4PeerManager` | `GET /api/kea/dhcpv4/get_peer`, `POST /api/kea/dhcpv4/search_peer` | `ABSENT` |

## Kea DHCPv6 (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| kea6-subnet | `Kea6SubnetManager` | `GET /api/kea/dhcpv6/get_subnet`, `POST /api/kea/dhcpv6/search_subnet` | `ABSENT` |
| kea6-reservation | `Kea6ReservationManager` | `GET /api/kea/dhcpv6/get_reservation`, `POST /api/kea/dhcpv6/search_reservation` | `ABSENT` |

## WireGuard (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| wg-server | `WgServerManager` | `GET /api/wireguard/server/get_server`, `POST /api/wireguard/server/search_server` | `ABSENT` |
| wg-client | `WgClientManager` | `GET /api/wireguard/client/get_client`, `POST /api/wireguard/client/search_client` | `ABSENT` |

## IPsec (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| ipsec-conn | `IpsecConnManager` | `GET /api/ipsec/connections/get_connection`, `POST /api/ipsec/connections/search_connection` | `ABSENT` |
| ipsec-psk | `IpsecPskManager` | `GET /api/ipsec/pre_shared_keys/get_item`, `POST /api/ipsec/pre_shared_keys/search_item` | `ABSENT` |
| ipsec-child | `IpsecChildManager` | `GET /api/ipsec/connections/get_child`, `POST /api/ipsec/connections/search_child` | `ABSENT` |
| ipsec-local | `IpsecLocalManager` | `GET /api/ipsec/connections/get_local`, `POST /api/ipsec/connections/search_local` | `ABSENT` |
| ipsec-remote | `IpsecRemoteManager` | `GET /api/ipsec/connections/get_remote`, `POST /api/ipsec/connections/search_remote` | `ABSENT` |
| ipsec-pool | `IpsecPoolManager` | `GET /api/ipsec/pools/get_item`, `POST /api/ipsec/pools/search_item` | `ABSENT` |
| ipsec-keypair | `IpsecKeypairManager` | `GET /api/ipsec/key_pairs/get_item`, `POST /api/ipsec/key_pairs/search_item` | `ABSENT` |
| ipsec-vti | `IpsecVtiManager` | `GET /api/ipsec/vti/get_item`, `POST /api/ipsec/vti/search_item` | `ABSENT` |

## Traffic Shaper (1 manager — requires reconfigure)

| Domain | Manager | Match keys | Endpoints | Status | Notes |
|---|---|---|---|---|---|
| ts-pipe | `TsPipeManager` | `description, bandwidth, bandwidthMetric` | `trafficshaper/settings` Pipe | `INTEGRATION_TEST_PASSED` | Bandwidth pipes |
| ts-queue | `TsQueueManager` | — | `trafficshaper/settings` Queue | `ABSENT` | |
| ts-rule | `TsRuleManager` | — | `trafficshaper/settings` Rule | `ABSENT` | |

## Syslog (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| syslog-dest | `SyslogDestManager` | `GET /api/syslog/settings/get_destination`, `POST /api/syslog/settings/search_destinations` | `ABSENT` |

## Cron (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| cron-job | `CronJobManager` | `GET /api/cron/settings/get_job`, `POST /api/cron/settings/search_jobs` | `ABSENT` |

## Trust / PKI

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| trust-ca | `TrustCaManager` | `GET /api/trust/ca/get`, `POST /api/trust/ca/search` | `ABSENT` |
| trust-cert | `TrustCertManager` | `GET /api/trust/cert/get`, `POST /api/trust/cert/search` | `ABSENT` |

## IDS / Suricata

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| ids-policy | `IdsPolicyManager` | `GET /api/ids/settings/get_policy`, `POST /api/ids/settings/search_policy` | `ABSENT` |
| ids-policy-rule | `IdsPolicyRuleManager` | `GET /api/ids/settings/get_policy_rule`, `POST /api/ids/settings/search_policy_rule` | `ABSENT` |
| ids-user-rule | `IdsUserRuleManager` | `GET /api/ids/settings/get_user_rule`, `POST /api/ids/settings/search_user_rule` | `ABSENT` |

## Captive Portal

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| cp-zone | `CpZoneManager` | `GET /api/captiveportal/settings/get_zone`, `POST /api/captiveportal/settings/search_zones` | `ABSENT` |

## OpenVPN

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| ovpn-instance | `OvpnInstanceManager` | `GET /api/openvpn/instances/get_instance`, `POST /api/openvpn/instances/search_instance` | `ABSENT` |
| ovpn-cso | `OvpnCsoManager` | `GET /api/openvpn/instances/get_cso`, `POST /api/openvpn/instances/search_cso` | `ABSENT` |

## DHCP Relay

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| dhcrelay-dest | `DhcrelayDestManager` | `GET /api/dhcrelay/settings/get_dest`, `POST /api/dhcrelay/settings/search_dest` | `ABSENT` |
| dhcrelay-relay | `DhcrelayRelayManager` | `GET /api/dhcrelay/settings/get_relay`, `POST /api/dhcrelay/settings/search_relay` | `ABSENT` |

## Monit

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| monit-alert | `MonitAlertManager` | `GET /api/monit/settings/get_alert`, `POST /api/monit/settings/search_alert` | `ABSENT` |
| monit-service | `MonitServiceManager` | `GET /api/monit/settings/get_service`, `POST /api/monit/settings/search_service` | `ABSENT` |
| monit-test | `MonitTestManager` | `GET /api/monit/settings/get_test`, `POST /api/monit/settings/search_test` | `ABSENT` |

## Dnsmasq

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| dnsmasq-host | `DnsmasqHostManager` | `GET /api/dnsmasq/settings/get_host`, `POST /api/dnsmasq/settings/search_host` | `ABSENT` |
| dnsmasq-domain | `DnsmasqDomainManager` | `GET /api/dnsmasq/settings/get_domain`, `POST /api/dnsmasq/settings/search_domain` | `ABSENT` |
| dnsmasq-boot | `DnsmasqBootManager` | `GET /api/dnsmasq/settings/get_boot`, `POST /api/dnsmasq/settings/search_boot` | `ABSENT` |
| dnsmasq-option | `DnsmasqOptionManager` | `GET /api/dnsmasq/settings/get_option`, `POST /api/dnsmasq/settings/search_option` | `ABSENT` |
| dnsmasq-range | `DnsmasqRangeManager` | `GET /api/dnsmasq/settings/get_range`, `POST /api/dnsmasq/settings/search_range` | `ABSENT` |
| dnsmasq-tag | `DnsmasqTagManager` | `GET /api/dnsmasq/settings/get_tag`, `POST /api/dnsmasq/settings/search_tag` | `ABSENT` |

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
