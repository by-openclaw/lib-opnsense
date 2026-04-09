<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# Auth Scope — lib-opnsense

## Overview

4 managers: AuthUserManager, AuthGroupManager, AuthPrivManager, AuthApiKeyManager.
Auth changes apply immediately — no reconfigure needed.
Users/groups are server-enforced unique (API rejects duplicates).

## Network Diagram

```
No network dependency — auth is local to OPNsense.
All operations are API-only, no traffic flow affected.

  Rune VM (10.100.0.101) → OPNsense API (10.6.239.114)
    └── POST /api/auth/user/add  → user created immediately
```

## Managers

### AuthUserManager (`auth/user`)

- Endpoint: auth/user
- Entity suffix: (standard search/get/add/set/del)
- Match key: name (unique, server-enforced)
- Redact: password, otp_seed, scrambled_password, authorizedkeys
- Module path: `opnsense.managers.auth.user`

### AuthGroupManager (`auth/group`)

- Endpoint: auth/group
- Match key: name (unique, server-enforced)
- Redact: none
- Module path: `opnsense.managers.auth.group`

### AuthPrivManager (custom, not BaseManager)

- Uses auth/user and auth/group endpoints for priv assignment
- Match key: N/A (assignment semantics)
- Module path: `opnsense.managers.auth.priv`

### AuthApiKeyManager (custom, not BaseManager)

- Endpoint: auth/user (add_api_key, search_api_key, del_api_key)
- Match key: N/A (key ID)
- Redact: key, secret (on creation only)
- Module path: `opnsense.managers.auth.api_key`

## Use Cases

### M01 — AuthUserManager

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create user | name=inttest-alice, email=alice@example.com, password=T3stP@ss! | changed=True, created | CRUD + no reconfigure |
| 02 | Idempotent noop | same params | changed=False, noop | diff engine |
| 03 | Read user | list(search_phrase=inttest-alice) | 1 match | search |
| 04 | Update email | email=alice-updated@example.com | changed=True, updated | drift detection |
| 05 | Update idempotent | same updated email | changed=False, noop | no false drift |
| 06 | check_mode delete | check_mode=True | changed=True but user exists | dry run |
| 07 | Delete user | state=absent | changed=True, deleted | delete works |
| 08 | Delete idempotent | already gone | changed=False, noop | absent noop |
| 09 | Error: duplicate create | direct create() on existing | OpnsenseValidationError | server-enforced |
| 10 | Error: invalid email | email=not-an-email | capture API response | validation shape |

### M02 — AuthGroupManager

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create group | name=inttest-engineers | created | CRUD |
| 02 | Idempotent noop | same | noop | diff |
| 03 | Update description | new description | updated | drift |
| 04 | Delete + idempotent | | deleted then noop | |
| 05 | User-group assignment | assign inttest-alice via GID | updated | memberships |
| 06 | Error: delete group with members | delete while users assigned | capture error | |

### M03 — AuthPrivManager

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Assign priv to group | priv_id=page-diagnostics-arptable, target_type=group | created | assignment |
| 02 | Idempotent noop | same | noop | no re-assign |
| 03 | Assign priv to user | target_type=user | created | user-level |
| 04 | check_mode unassign | check_mode=True | changed but still assigned | dry run |
| 05 | Unassign + idempotent | | deleted then noop | |
| 06 | Error: invalid target_type | target_type=invalid | ValueError | client-side |
| 07 | Error: nonexistent user | target_name=nonexistent | capture error | API error |

### M04 — AuthApiKeyManager

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create API key | username=inttest-bob | key + secret returned | create |
| 02 | List keys | filter by username | >= 1 key | list |
| 03 | Create second key | same user | multiple keys per user | no conflict |
| 04 | check_mode delete_all | | changed but keys exist | dry run |
| 05 | Delete all + idempotent | | deleted then noop | |
| 06 | Error: nonexistent user | username=nonexistent-99 | OpnsenseError | API error |

## Bill of Materials

No infrastructure required — auth is local to OPNsense.
- OPNsense test device: 10.6.239.114
- API key: svc-rune

## Safety Boundaries

- inttest- prefix only for all test users/groups
- NEVER touch: root, svc-rune, admins group, system users
- Safe read-only privileges only: page-diagnostics-*, page-status-*
- NEVER assign page-all or admin privs to test users

## Test Status

| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All CRUD, ensure, check_mode, error handling |
| Integration tests | PASS | Full lifecycle on live device |
