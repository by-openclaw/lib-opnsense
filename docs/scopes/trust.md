<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# Trust / PKI Scope — lib-opnsense

## Overview
2 managers: TrustCaManager, TrustCertManager.
CA supports import and generate. Cert uses CA refid (NOT UUID) for caref field.
Both redact private keys (prv, prv_payload).

## Sequence Diagram — Certificate Chain
```
  1. Create/Import CA
     │
     │ CA refid (from search result, NOT UUID)
     ▼
  2. Create/Import Cert (caref = CA refid)
     │
     │ cert refid
     ▼
  3. OpenVPN / other services reference cert by refid
```

## Managers
- TrustCaManager: trust/ca. Match: descr. Redact: prv, prv_payload. Module: `opnsense.managers.trust.ca`
- TrustCertManager: trust/cert. Match: descr. Redact: prv, prv_payload. Uses CA refid not UUID. Module: `opnsense.managers.trust.cert`

## Use Cases

### TrustCaManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Generate CA | descr=inttest-ca, key_type=RSA, key_length=2048 | created | CA generation |
| 02 | Import CA | descr=inttest-ca-import, crt=<PEM> | created | CA import |
| 03 | Delete | | deleted | |
| 04 | **Duplicate: same descr** | descr=inttest-ca (exists) | AmbiguousMatchError or API rejection | duplicate guard |

### TrustCertManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Generate cert | descr=inttest-cert, caref=<CA-refid> | created | needs CA refid |
| 02 | Delete | | deleted | |
| 03 | Error: UUID instead of refid | caref=<UUID> | API rejection | refid required |

## Bill of Materials
- OPNsense test device
- No LXC required

## Safety Boundaries
- inttest- prefix on all CA/cert descriptions
- Never touch production CAs or certs
- Private keys redacted in logs (prv, prv_payload)

## CRUD Verification

API CRUD must be confirmed on the device, not just by API response.

| After CRUD | Verify with | From | Expected |
|---|---|---|---|
| Create CA | `ssh root@10.6.239.114 "openssl x509 -in /var/db/opnsense/... -text"` or WebGUI Trust → Authorities | OPNsense SSH / WebGUI | CA certificate visible |
| Create cert | WebGUI Trust → Certificates | WebGUI | cert listed, signed by inttest-ca |
| Cert chain valid | `openssl verify -CAfile ca.pem cert.pem` | OPNsense SSH | OK |
| Delete CA | WebGUI Trust → Authorities | WebGUI | inttest-ca gone |

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.trust.ca    → TrustCaManager
opnsense.managers.trust.cert  → TrustCertManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.trust"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | Both managers |
| Integration tests | PASS | Generate + import |
