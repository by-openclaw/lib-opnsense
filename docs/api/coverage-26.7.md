# OPNsense 26.7 — MVC API coverage vs lib-opnsense

> Source of truth: route discovery on a live **OPNsense 26.7 (CE)** test FW
> (`vm-opns-test-01`), enumerated from `/usr/local/opnsense/mvc/app/controllers/
> OPNsense/*/Api/*Controller.php` (public `*Action` methods).
> Full catalog: [`data/26.7/endpoints.txt`](data/26.7/endpoints.txt) — **812 endpoints / 117 controllers**.

## Headline
| | count |
|---|---|
| API controllers in 26.7 | 117 |
| Covered by a lib manager | 32 |
| **CONFIG controllers not yet covered (backlog)** | **19** |
| Diagnostics / status / service-only (low priority) | 66 |

## The 100% MVC backlog (configurable controllers, prioritized)
| Controller | Actions | Priority | Note |
|---|---|---|---|
| `routing/groupsettings` | add/del/get/set/search/reconfigure | **HIGH** | Gateway **groups** → multi-WAN failover/PBR (Proximus+Telenet) |
| `trust/ca` | add/del/get/set/search + caInfo/generateFile | **HIGH** | Certificate Authority management (was XML-only) |
| `trust/cert` | add/del/get/set/search + userList | **HIGH** | Certificate management |
| `trust/crl` | add/del/get/set/search | MED | Revocation lists |
| `ipsec/connections` | addConnection/addChild/addLocal/addRemote/... | **HIGH** | IPsec (swanctl connections model) |
| `ipsec/pools` | add/del/get/set/search/toggle | MED | IPsec address pools |
| `ipsec/vti` | add/del/get/set/search/toggle | MED | IPsec VTI |
| `ipsec/manualspd` | add/del/get/set/search/toggle | LOW | Manual SPD |
| `ipsec/tunnel` | search/del/toggle Phase1/Phase2 | LOW | Legacy tunnel (deprecated by connections) |
| `openvpn/instances` | add/del/get/set/search + genKey/StaticKey | **HIGH** | OpenVPN (new instances model) |
| `openvpn/clientoverwrites` | add/del/get/set/search/toggle | MED | Per-CN overrides |
| `core/snapshots` | add/del/get/set/search/activate | MED | Config snapshots (boot-env) |
| `auth/group` | add/del/get/set/search | verify | lib has `auth/group.py` — confirm parity |
| `firewall/aliasutil` | add/delete/aliases/flush/findReferences | LOW | Alias runtime helpers (alias CRUD already covered) |

Diagnostics with a `set` action (`diagnostics/ping|traceroute|portprobe|packetcapture|dnsdiagnostics`)
are operational tools, not config — wrap only if a playbook needs them.

## Method
Route discovery (no writes): enumerate controllers/actions on the FW. Schema probe
(read-only): `scripts/probe-api-schemas.sh` → `data/26.7/`. See
[`discovery-methodology.md`](discovery-methodology.md).
