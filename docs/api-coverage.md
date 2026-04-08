# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense

# API Coverage — lib-opnsense

> Probed against OPNsense **26.1.5** — 200/200 endpoints OK.
> Probe data: `docs/api/data/26.1.5/`
> Last updated: 2026-04-07

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
| Managers done (integration tested) | 6 |
| Managers done (unit tested) | 5 |
| Managers partial | 2 |
| Managers absent (CRUD) | 53 |
| Managers absent (read-only) | 68 |

---

## Auth (immediate, no reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| auth-user | `AuthUserManager` | `GET /api/auth/user/get`, `POST /api/auth/user/search` | `INTEGRATION_TEST_PASSED` |
| auth-group | `AuthGroupManager` | `GET /api/auth/group/get`, `POST /api/auth/group/search` | `INTEGRATION_TEST_PASSED` |
| auth-priv | `AuthPrivManager` | `GET /api/auth/priv/get` | `INTEGRATION_TEST_PASSED` |
| auth-user (API keys) | `AuthApiKeyManager` | `POST /api/auth/user/search_api_key/{uid}` | `INTEGRATION_TEST_PASSED` |

## Firewall — Filter (requires apply)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| fw-filter-rule | `FwFilterManager` | `GET /api/firewall/filter/get_rule`, `POST /api/firewall/filter/search_rule` | `INTEGRATION_TEST_PASSED` |
| fw-alias | `FwAliasManager` | `GET /api/firewall/alias/get_item`, `POST /api/firewall/alias/search_item` | `INTEGRATION_TEST_PASSED` |
| fw-category | `FwCategoryManager` | `GET /api/firewall/category/get_item`, `POST /api/firewall/category/search_item` | `UNIT_TEST_PASSED` |
| fw-group | `FwGroupManager` | `GET /api/firewall/group/get_item`, `POST /api/firewall/group/search_item` | `UNIT_TEST_PASSED` |

## Firewall — NAT (requires apply)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| fw-dnat-rule | `FwDnatManager` | `GET /api/firewall/d_nat/get_rule`, `POST /api/firewall/d_nat/search_rule` | `INTEGRATION_TEST_PASSED` |
| fw-snat-rule | `FwSourceNatManager` | `GET /api/firewall/source_nat/get_rule`, `POST /api/firewall/source_nat/search_rule` | `UNIT_TEST_PASSED` |
| fw-1to1-rule | `FwOneToOneManager` | `GET /api/firewall/one_to_one/get_rule`, `POST /api/firewall/one_to_one/search_rule` | `UNIT_TEST_PASSED` |
| fw-npt-rule | `FwNptManager` | `GET /api/firewall/npt/get_rule`, `POST /api/firewall/npt/search_rule` | `ABSENT` |

## Interfaces (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| if-vlan | `IfVlanManager` | `GET /api/interfaces/vlan_settings/get_item`, `POST /api/interfaces/vlan_settings/search_item` | `PARTIAL` |
| if-vip | `IfVipManager` | `GET /api/interfaces/vip_settings/get_item`, `POST /api/interfaces/vip_settings/search_item` | `PARTIAL` |
| if-bridge | `IfBridgeManager` | `GET /api/interfaces/bridge_settings/get_item`, `POST /api/interfaces/bridge_settings/search_item` | `ABSENT` |
| if-gif | `IfGifManager` | `GET /api/interfaces/gif_settings/get_item`, `POST /api/interfaces/gif_settings/search_item` | `ABSENT` |
| if-gre | `IfGreManager` | `GET /api/interfaces/gre_settings/get_item`, `POST /api/interfaces/gre_settings/search_item` | `ABSENT` |
| if-lagg | `IfLaggManager` | `GET /api/interfaces/lagg_settings/get_item`, `POST /api/interfaces/lagg_settings/search_item` | `ABSENT` |
| if-loopback | `IfLoopbackManager` | `GET /api/interfaces/loopback_settings/get_item`, `POST /api/interfaces/loopback_settings/search_item` | `ABSENT` |
| if-neighbor | `IfNeighborManager` | `GET /api/interfaces/neighbor_settings/get_item`, `POST /api/interfaces/neighbor_settings/search_item` | `ABSENT` |
| if-vxlan | `IfVxlanManager` | `GET /api/interfaces/vxlan_settings/get_item`, `POST /api/interfaces/vxlan_settings/search_item` | `ABSENT` |

## Routing (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| route | `RtRouteManager` | `GET /api/routes/routes/get_route`, `POST /api/routes/routes/search_route` | `ABSENT` |
| routing-gw | `RtGatewayManager` | `GET /api/routing/settings/get_gateway`, `POST /api/routing/settings/search_gateway` | `ABSENT` |

## Unbound DNS (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| ub-forward | `UbForwardManager` | `GET /api/unbound/settings/get_forward`, `POST /api/unbound/settings/search_forward` | `ABSENT` |
| ub-host-override | `UbHostOverrideManager` | `GET /api/unbound/settings/get_host_override`, `POST /api/unbound/settings/search_host_override` | `ABSENT` |
| ub-host-alias | `UbHostAliasManager` | `GET /api/unbound/settings/get_host_alias`, `POST /api/unbound/settings/search_host_alias` | `ABSENT` |
| ub-acl | `UbAclManager` | `GET /api/unbound/settings/get_acl`, `POST /api/unbound/settings/search_acl` | `ABSENT` |
| ub-dnsbl | `UbDnsblManager` | `GET /api/unbound/settings/get_dnsbl`, `POST /api/unbound/settings/search_dnsbl` | `ABSENT` |

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

## Traffic Shaper (requires reconfigure)

| Domain | Manager | Endpoints | Status |
|---|---|---|---|
| ts-pipe | `TsPipeManager` | `GET /api/trafficshaper/settings/get_pipe`, `POST /api/trafficshaper/settings/search_pipe` | `UNIT_TEST_PASSED` |
| ts-queue | `TsQueueManager` | `GET /api/trafficshaper/settings/get_queue`, `POST /api/trafficshaper/settings/search_queue` | `ABSENT` |
| ts-rule | `TsRuleManager` | `GET /api/trafficshaper/settings/get_rule`, `POST /api/trafficshaper/settings/search_rule` | `ABSENT` |

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
| ub-diag-stats | `UbDiagStatsManager` | `GET /api/unbound/diagnostics/stats` | `ABSENT` |
| wg-show | `WgShowManager` | `GET /api/wireguard/service/show` | `ABSENT` ||
