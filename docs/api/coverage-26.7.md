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


## Live verification (2026-09-06, against the 26.7 CE test FW)
The crude name-diff over-counted the gap. Accurate mapping (f-string endpoints
included): **lib covers 53 controllers**; the true CONFIG gap is small, and each
was probed LIVE:

| Controller | Live status | Verdict |
|---|---|---|
| `trust/ca`, `trust/cert` | 200 | already covered (TrustCa/TrustCertManager) |
| `ipsec/connections,vti,pool,...` | — | already covered (vpn/ipsec_* managers) |
| `openvpn/instances` | 200 | already covered (OvpnInstanceManager) |
| **`trust/crl`** | **200** | **GAP — buildable now (completes PKI); set-per-CA lifecycle** |
| **`core/snapshots`** | 200 (ZFS-gated; `isSupported`=400 on this UFS nano) | GAP — needs a ZFS FW to integration-test |
| `openvpn/clientoverwrites` | **404** | source exists, route NOT live on 26.7 nano — cannot integration-test |
| `routing/groupsettings` (gateway groups) | **404** | source exists, route NOT live — blocks the multi-WAN failover manager |
| `ipsec/manualspd`, `ipsec/tunnel` | — | legacy (superseded by connections) — skip |
| `firewall/aliasutil`, `diagnostics/*` | — | runtime/diagnostic helpers, not config managers |

**Route-404 finding:** `clientoverwrites` and `groupsettings` controllers exist in
`/usr/local/opnsense/mvc/app/controllers/.../Api/` but `/api/.../search` returns 404
on this 26.7 CE **nano** build. Needs verifying on a full (DVD) install before their
managers can be integration-tested and merged (lib rule: no merge without integration tests).

**Net:** lib is at/near 100% of the *live, config* MVC surface on 26.7. Remaining real
work: `trust/crl` (buildable), `core/snapshots` (needs ZFS), and confirming the two
route-404 controllers on a full install.


## DEFINITIVE (2026-09-06, full ZFS 26.7 CE install — vm-opns-lab-01)
Rebuilt a **fresh full DVD/serial install of 26.7 CE on ZFS** (not nano) to settle the
route-404 controllers. Result: `openvpn/clientoverwrites/search` and
`routing/groupsettings/search` **STILL 404 on the full install** — these controllers exist
in the PHP source but are **not API-routed in 26.7 CE** (GUI-only / not wired). They are
therefore NOT part of the live MVC surface and NOT lib gaps. Gateway groups have no MVC API
in 26.7 CE (only `routing/settings/*Gateway*` for gateways) — a lib gateway-group manager
would need the config.xml/uri workaround, not MVC.

**The lib is at 100% of the live, config MVC surface on 26.7 CE except two controllers, both
now confirmed live + testable on the ZFS lab FW:**
- `trust/crl` (200) — completes PKI; set-per-CA lifecycle.
- `core/snapshots` **DONE** (CoreSnapshotManager + integration tests, verified on the ZFS lab) (was: 200; ZFS — `search` returns the live "default" boot-env snapshot) — config/boot-env snapshots.

Building those two (with integration tests against vm-opns-lab-01) reaches 100%.


## FINAL (2026-09-06) — coverage outcome
- **`core/snapshots`: DONE** — `CoreSnapshotManager` + 6 integration tests (ZFS lab). Gap closed.
- **`trust/crl`: not a clean manager target.** Live-probed on 26.7: actions are `search/get/set/del`
  (+ getOcspInfoData/rawDump) with **NO `add`**, and `set`/`get` require a uuid (bare `set` → 404).
  CRLs are DERIVED — generated per-CA and on certificate revocation — not directly created, so an
  `ensure(present)` manager is not meaningful. Covered operationally by the CA/cert flow
  (TrustCaManager/TrustCertManager). Documented as intentionally not-managed.
- `openvpn/clientoverwrites`, `routing/groupsettings`: not API-routed in 26.7 CE (source-only) — not gaps.

**Result: lib-opnsense is at 100% of the live, cleanly-manageable config MVC surface on 26.7 CE.**
Non-config diagnostics/service controllers (ping, packetcapture, etc.) are operational tools, wrapped
only if a playbook needs them.
