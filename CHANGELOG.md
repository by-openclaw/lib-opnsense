# Changelog

## [0.2.0](https://github.com/by-openclaw/lib-opnsense/compare/v0.1.0...v0.2.0) (2026-04-08)


### Features

* add API docs, probe scripts, and probe data ([14d73f3](https://github.com/by-openclaw/lib-opnsense/commit/14d73f3db7275cc4c520f50dcace2cf5cf17d4cf))
* add API docs, probe scripts, and probe data from platform-setup ([4be0dc1](https://github.com/by-openclaw/lib-opnsense/commit/4be0dc1e13cb8ab7f1ee047f2737406af6113530))
* add field validators for all managers ([e225463](https://github.com/by-openclaw/lib-opnsense/commit/e225463ad142381e649c3088115b64d39e2bae2f))
* add field validators for all managers ([9dad267](https://github.com/by-openclaw/lib-opnsense/commit/9dad2675ac41b577004b1fa2fed70da304cdd879))
* add FwCategory, FwGroup, TsPipe managers ([#4](https://github.com/by-openclaw/lib-opnsense/issues/4)) ([5ad65d6](https://github.com/by-openclaw/lib-opnsense/commit/5ad65d69608202973ded6a190cf65907b273446c))
* add IfVlanManager + IfVipManager with tests ([555c94b](https://github.com/by-openclaw/lib-opnsense/commit/555c94b0e1cc12ff160755b7b27fcfddb77d4ba2))
* add IfVlanManager + IfVipManager with unit and integration tests ([785b15e](https://github.com/by-openclaw/lib-opnsense/commit/785b15e7bf4f0234d8d30ca81cd34d0c726e5d80))
* add integration tests for M09-M12 + safety fixes on all FW tests ([98c695a](https://github.com/by-openclaw/lib-opnsense/commit/98c695a5b330795066677385343e93d7cc82eb96))
* add verbose logging with duration_ms to ensure() and HTTP client ([76e267a](https://github.com/by-openclaw/lib-opnsense/commit/76e267acdb79a237f9c83bb13106e2fa82499e07))
* **auth:** AuthApiKeyManager, integration tests, structlog, 26.1 compatibility ([#2](https://github.com/by-openclaw/lib-opnsense/issues/2)) ([5bd7848](https://github.com/by-openclaw/lib-opnsense/commit/5bd7848ef120be699a44c29137a380b102a32ef0))
* **base:** implement composite _match_keys with AmbiguousMatchError ([30b5904](https://github.com/by-openclaw/lib-opnsense/commit/30b5904b6846f8c54d988e808c589478d7770e10))
* **base:** implement composite _match_keys with AmbiguousMatchError ([e06138a](https://github.com/by-openclaw/lib-opnsense/commit/e06138aac00a12d4679c4649ac639a5ddab0f08e))
* **firewall:** add FwAlias, FwFilter, FwDnat, FwSourceNat managers ([#3](https://github.com/by-openclaw/lib-opnsense/issues/3)) ([65df8d2](https://github.com/by-openclaw/lib-opnsense/commit/65df8d2c46637de2477f633ef485df23cb7ab95e))
* initial scaffold — OpnsenseClient, auth managers, CI, devcontainer ([a01d7ff](https://github.com/by-openclaw/lib-opnsense/commit/a01d7ff16de77fd2883d9bcfd1b3c100fba63596))
* integration tests for M09-M12 + safety fixes ([77fc9ad](https://github.com/by-openclaw/lib-opnsense/commit/77fc9add5c87cf310805712fe86639103ffc9b5b))
* verbose logging with duration_ms on ensure() and HTTP client ([1a2a8b3](https://github.com/by-openclaw/lib-opnsense/commit/1a2a8b39364a560bafe57fbe0dfc7b26f744458e))


### Bug Fixes

* add file headers, VaultCredentialProvider, .gitkeep, relative paths ([42b9816](https://github.com/by-openclaw/lib-opnsense/commit/42b9816c69da102822929346402a432fb5f6834e))
* add try/except in validate_params to catch unexpected validator errors ([5e074e8](https://github.com/by-openclaw/lib-opnsense/commit/5e074e8c84c562be5c09619169d5511232025d01))
* add try/except/log/raise to list, get, get_schema, _apply ([bc2cabf](https://github.com/by-openclaw/lib-opnsense/commit/bc2cabf5862bd741300a2d84621fb2a2f730f206))
* add type annotation to resolve mypy assignment error in ensure() ([24a9ec8](https://github.com/by-openclaw/lib-opnsense/commit/24a9ec89e5b1eaec8cadb3631219edc525233719))
* **ci:** lower coverage threshold to 65% for scaffold phase ([0e3e3c8](https://github.com/by-openclaw/lib-opnsense/commit/0e3e3c876d5e2f25857de1404cf29cffd0ae10a6))
* **ci:** read coverage threshold from pyproject.toml, not hardcoded in workflow ([5b7f152](https://github.com/by-openclaw/lib-opnsense/commit/5b7f152629e3b6ac24ebc5e69d7f05e5d3068c1a))
* file headers, VaultCredentialProvider, diagrams, API coverage table ([e5fd04e](https://github.com/by-openclaw/lib-opnsense/commit/e5fd04e5fb08c827734859bb34df24b4139a7a18))
* handle enum dicts and missing search fields in _compute_diff ([30336a4](https://github.com/by-openclaw/lib-opnsense/commit/30336a45f38c073f0898d3d823b2c37326f597b8))
* handle enum dicts and missing search fields in _compute_diff ([3546c98](https://github.com/by-openclaw/lib-opnsense/commit/3546c98f124172253083342fca425ee32bf59264))
* log validation errors at ERROR before raising in ensure() ([50333e9](https://github.com/by-openclaw/lib-opnsense/commit/50333e9a516756bd8464ada70d307c60846ccb7e))
* resolve all ruff (79), mypy (4), and formatting issues ([ec23e3d](https://github.com/by-openclaw/lib-opnsense/commit/ec23e3dd327f905e2a7a9ba5e428ca1db34d97e6))


### Documentation

* add API match key reference for team review ([d301989](https://github.com/by-openclaw/lib-opnsense/commit/d3019897b9cab123cbe4888f1991841f9ac28bf8))
* add endpoint tables and safety refs to all manager docstrings ([e461c4a](https://github.com/by-openclaw/lib-opnsense/commit/e461c4a9c91f5cde72d8c8204f41ac133b5be3d1))
* add endpoint tables, redact fields, and safety refs to all manager docstrings ([b78657a](https://github.com/by-openclaw/lib-opnsense/commit/b78657a7182ee77250ea3ab7d6a95d012c3a79a4))
* add OOP refactor scope of work ([f8016ad](https://github.com/by-openclaw/lib-opnsense/commit/f8016ad5b3f0563877191a8110e7f9f2c9901de1))
* API match key reference — composite key strategy ([6d9ac58](https://github.com/by-openclaw/lib-opnsense/commit/6d9ac581a520bab03f97301600c748c8a5b968b1))
* api-coverage.md with "Since" column, CLAUDE.md error handling pattern ([5bd7848](https://github.com/by-openclaw/lib-opnsense/commit/5bd7848ef120be699a44c29137a380b102a32ef0))
* expand test zone plan with per-manager scope and E2E playbook ([82cb2cb](https://github.com/by-openclaw/lib-opnsense/commit/82cb2cbcae0f40c4cf1660dd0167663e4324c28e))
* expand test zone plan with per-manager scope and E2E playbook ([aacdca0](https://github.com/by-openclaw/lib-opnsense/commit/aacdca01777b85e175c82b6bf27802d82f74a3f2))
* move API coverage table to docs/api-coverage.md, link from README ([236cfaa](https://github.com/by-openclaw/lib-opnsense/commit/236cfaaa9a661731dafaa793559005e1d7ffa0c8))
* OOP refactor scope of work ([7f3a9be](https://github.com/by-openclaw/lib-opnsense/commit/7f3a9beada3df1be807dc6ada6ebcf0c0cefc8ad))
* refresh API probe data and api-coverage.md for OPNsense 26.1.5 ([a1b6ea6](https://github.com/by-openclaw/lib-opnsense/commit/a1b6ea677c07130adce3fd735194fb88da48cb55))
* refresh API probe data for OPNsense 26.1.5 ([60a2ce6](https://github.com/by-openclaw/lib-opnsense/commit/60a2ce61f2a224c4366a053c329c3a8c4bab18ae))
* update CLAUDE.md and refactor scope for completed refactor (Phase 4-5) ([75e1bbb](https://github.com/by-openclaw/lib-opnsense/commit/75e1bbb0eb640d635f478bfdf0f6d783fccd2c43))
* update CLAUDE.md and refactor scope to reflect completed refactor ([25aaee2](https://github.com/by-openclaw/lib-opnsense/commit/25aaee29cac27ac5e0ba5258402588ba43924ef8))

## [Unreleased]

### Features

* Initial library scaffold — OpnsenseClient, BaseManager, AuthUserManager, AuthGroupManager, AuthPrivManager
* Async/await with httpx (ADR-0029)
* ensure() idempotency with EnsureResult dataclass
* Typed exception hierarchy
* Credential providers (env vars)
