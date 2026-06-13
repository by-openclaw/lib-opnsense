<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# ACME / Certificates Scope — lib-opnsense

## Overview
6 managers wrapping the **os-acme-client** plugin (`/api/acmeclient/*`): issue and
renew ACME (Let's Encrypt) certificates on OPNsense — e.g. a CA-issued WebGUI
cert (no browser warning, auto-renew). Verified live against **os-acme-client
4.16** on OPNsense 26.1.9.

- `AcmeSettingsManager` — plugin-wide settings (singleton).
- `AcmeServiceManager` — service control (status/reconfigure/configtest).
- `AcmeAccountManager` — ACME accounts (which CA) + `register`.
- `AcmeValidationManager` — challenge config (HTTP-01 / DNS-01 / TLS-ALPN-01).
- `AcmeCertificateManager` — certificates + `sign`/`revoke`/`removekey`/`automation`/`import`.
- `AcmeActionManager` — post-issue automation (e.g. restart the WebGUI).

## Sequence Diagram — issue a WebGUI certificate (DNS-01 / Cloudflare)
```
  1. AcmeSettingsManager.ensure(present, {enabled:1})         # enable plugin
     │
  2. AcmeAccountManager.ensure(present, {ca:letsencrypt,…})   # define account
     │  └─ AcmeAccountManager.register(uuid)                  # register w/ CA
     ▼
  3. AcmeValidationManager.ensure(present, {                  # DNS-01 challenge
        method:dns01, dns_service:dns_cf, dns_cf_token:…})
     │
  4. AcmeActionManager.ensure(present, {                      # restart GUI after
        type:configd_restart_gui})                            #   issue/renew
     ▼
  5. AcmeCertificateManager.ensure(present, {                 # tie it together
        name:fw.example.com, account:<uuid>,
        validationMethod:<uuid>, restartActions:<uuid>})
     │  └─ AcmeCertificateManager.sign(uuid)                  # issue → certRefId
     ▼
  6. System → Settings → Administration → SSL cert = certRefId  (WebGUI serves it)
```

## Managers
- `AcmeSettingsManager`: acmeclient/settings. Singleton (`BaseSingletonManager`).
  Nests under `settings`. Apply `acmeclient/service/reconfigure`. Module:
  `opnsense.managers.acme.settings`
- `AcmeServiceManager`: acmeclient/service. `BaseServiceManager` + `configtest()`.
  Module: `opnsense.managers.acme.service`
- `AcmeAccountManager`: acmeclient/accounts (bare). Match: `name`. Custom verb
  `register(uuid)`. Redact: key, eab_hmac, eab_kid. Module:
  `opnsense.managers.acme.accounts`
- `AcmeValidationManager`: acmeclient/validations (bare). Match: `name`. Common +
  Cloudflare DNS-01 fields typed; ~119 other DNS providers pass through. Redact:
  provider secrets. Module: `opnsense.managers.acme.validations`
- `AcmeCertificateManager`: acmeclient/certificates (bare). Match: `name`. Custom
  verbs `sign`/`revoke`/`remove_key`/`automation`/`import_`. `account`/
  `validationMethod`/`restartActions` are UUID refs. Module:
  `opnsense.managers.acme.certificates`
- `AcmeActionManager`: acmeclient/actions (bare). Match: `name`. `configd_restart_gui`
  to restart the WebGUI post-issue. Redact: remote-target credentials. Module:
  `opnsense.managers.acme.actions`

## Notes / gotchas
- **CRUD does not auto-apply.** Accounts/validations/certificates/actions store
  config immediately (`_apply_endpoint=None`); activation is explicit —
  `AcmeAccountManager.register`, `AcmeCertificateManager.sign`, and a single
  `AcmeServiceManager.reconfigure()` after a batch to regenerate cron/acme.sh cfg.
- **Enums read as option-dicts, write as strings.** Pass plain enum strings to
  `ensure()` (e.g. `keyLength="key_4096"`); the `DiffEngine` normalises the
  option-dict the API returns on read for idempotent diffing.
- **Cloudflare DNS-01** uses the scoped-token model: `dns_service="dns_cf"` +
  `dns_cf_token` (+ optional `dns_cf_account_id`/`dns_cf_zone_id`). The same
  Cloudflare token the platform's lego/ddns uses can be reused.
- **Never log secrets** — account keys, EAB HMAC and DNS provider tokens are in
  `REDACT_FIELDS`.
