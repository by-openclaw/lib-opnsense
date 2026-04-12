# Changelog

## [1.1.0](https://github.com/by-openclaw/lib-opnsense/compare/v1.0.0...v1.1.0) (2026-04-12)


### Features

* add self-contained TF config for integration test infra ([1cb43be](https://github.com/by-openclaw/lib-opnsense/commit/1cb43befd6afc8848d4087b5c3e2e83941b7d151))


### Bug Fixes

* **api:** bcrypt diff, 14 enum fixes, port regex, test split 49 files ([505e706](https://github.com/by-openclaw/lib-opnsense/commit/505e7064c6cd5e09cd20e99f5571a7238e63a97a))
* **api:** bcrypt diff, 14 enum fixes, port regex, test split 49 files ([14077a8](https://github.com/by-openclaw/lib-opnsense/commit/14077a8ba64fe6941d7cb9008d1ff626bdc7e5c8))
* move TF to infra/terraform/, add IPv6 subnets ([054ebc2](https://github.com/by-openclaw/lib-opnsense/commit/054ebc29e9b5d830044129a73334f72530302c5f))
* remove IPv6 SDN subnets — IPv6 configured on OPNsense ([7d37783](https://github.com/by-openclaw/lib-opnsense/commit/7d377831a4219839fcb74b5738b1fdbf959248ae))
* update TF node name srv-proxmox-poc-01 → srv-proxmox-01 ([d8cff3c](https://github.com/by-openclaw/lib-opnsense/commit/d8cff3c4a841a585b2624d22314a620368fd9af3))


### Documentation

* Docs:  ([14077a8](https://github.com/by-openclaw/lib-opnsense/commit/14077a8ba64fe6941d7cb9008d1ff626bdc7e5c8))
* add infra/ with integration test bootstrap guide ([794cc41](https://github.com/by-openclaw/lib-opnsense/commit/794cc415ec912f8b47a728efa3471ff056e02c2f))
* corrected network layout — vmbrMGMT for prod, test behind OPNsense ([7e3d445](https://github.com/by-openclaw/lib-opnsense/commit/7e3d44574d76a8282f313969ad69badc9c956af1))
* keep root SSH for bootstrap + OOB, disable after Phase 3 ([308cf8d](https://github.com/by-openclaw/lib-opnsense/commit/308cf8d404428a9d024b8e19ded55ea2dcf4936d))
* rename vmbrMGMT → vmbrOOB in all docs ([086e80c](https://github.com/by-openclaw/lib-opnsense/commit/086e80c0dc0d6b870dc5553f45372b74e05197a4))
* SSH access for non-root users — shell + pubkey required ([8e72b99](https://github.com/by-openclaw/lib-opnsense/commit/8e72b995585aeb1e827c1d53618369dbdf82af44))

## [1.0.0](https://github.com/by-openclaw/lib-opnsense/compare/v0.5.0...v1.0.0) (2026-04-09)


### ⚠ BREAKING CHANGES

* add package docstrings and fix smoke test
* update all import paths to scoped packages
* All import paths change. Module layout now uses scope packages instead of flat files:

### Bug Fixes

* add port_or_alias validator, fix port field types ([b4d3112](https://github.com/by-openclaw/lib-opnsense/commit/b4d31122197a5c2e89eb6f0a405bfe2530c7aa61))
* nwdiag syntax — remove unsupported description attribute ([a7fa827](https://github.com/by-openclaw/lib-opnsense/commit/a7fa8273b91a554712f197c8c4eed43cb3bf5af0))
* revert port field types to str, add port-field-reference doc ([64e56fc](https://github.com/by-openclaw/lib-opnsense/commit/64e56fcf7ceb6fc0dc145dd5bad162c222bcfce3))


### Documentation

* add CRUD verification commands to all scope docs ([3b28ca2](https://github.com/by-openclaw/lib-opnsense/commit/3b28ca2b541f2ec5243049c066b7d364bca9edc0))
* add per-scope documentation (10 scope files) ([e930f9e](https://github.com/by-openclaw/lib-opnsense/commit/e930f9ec61e1630ce41881b649104f31a04ce218))
* enhance scope docs with diagrams, BoM, granular VPN rules ([d26b755](https://github.com/by-openclaw/lib-opnsense/commit/d26b7555d120e89fd0771f1611e3ac1ea3b29675))
* update CLAUDE.md and README.md for v1.0.0 scope layout ([5be261d](https://github.com/by-openclaw/lib-opnsense/commit/5be261d9a435dfb1698b6ba6c9a75756b956c5d4))


### Code Refactoring

* add package docstrings and fix smoke test ([5a3603c](https://github.com/by-openclaw/lib-opnsense/commit/5a3603cad38721ce21a0f2921e5d9ee1517a270f))
* reorganize managers, models, tests by scope ([fd5f975](https://github.com/by-openclaw/lib-opnsense/commit/fd5f975a7b4da906c1711c24783cc706b8bc8e4e))
* update all import paths to scoped packages ([c59bd68](https://github.com/by-openclaw/lib-opnsense/commit/c59bd68806a5b06ab56c4f60ecaa0d3a38eb5b03))

## [0.5.0](https://github.com/by-openclaw/lib-opnsense/compare/v0.4.0...v0.5.0) (2026-04-08)


### Features

* add DdnsAccountManager — DynDNS A/AAAA updates (Cloudflare, AWS, etc.) ([3b0eb42](https://github.com/by-openclaw/lib-opnsense/commit/3b0eb42de1e81e9c45b920e8f3f78808e6882fb6))

## [0.4.0](https://github.com/by-openclaw/lib-opnsense/compare/v0.3.1...v0.4.0) (2026-04-08)


### Features

* 8 IPsec managers — full VPN tunnel management ([82ad6f2](https://github.com/by-openclaw/lib-opnsense/commit/82ad6f2bfdc951dfd49b9e847ddf5444c7befd99))
* add 8 IPsec managers — full VPN tunnel management ([5f9a859](https://github.com/by-openclaw/lib-opnsense/commit/5f9a8595c268fe1ee02b81f6c80b41d211919e83))
* add OvpnInstanceManager — OpenVPN server/client instances ([8c3624e](https://github.com/by-openclaw/lib-opnsense/commit/8c3624e97665765aafb58c24683dee73722bf201))
* add PluginManager + CronJobManager + mark Monit SKIPPED ([242307e](https://github.com/by-openclaw/lib-opnsense/commit/242307e81b4e2d030f63a5e0539b2f05746fe05c))
* add Trust/PKI (CA + Cert) + Captive Portal managers ([20a8bcd](https://github.com/by-openclaw/lib-opnsense/commit/20a8bcdc21e90def891f8acaea41a4d415214e24))
* OvpnInstanceManager — OpenVPN server/client (needs CA + cert) ([736a859](https://github.com/by-openclaw/lib-opnsense/commit/736a8592d616188170338dc0a30484bf13c8e22e))
* PluginManager + CronJobManager + Monit SKIPPED ([fded61d](https://github.com/by-openclaw/lib-opnsense/commit/fded61d14115a84c013cfb2914e2f2991271cc48))
* Trust/PKI (CA + Cert) + Captive Portal — 3 managers ([7424544](https://github.com/by-openclaw/lib-opnsense/commit/7424544fe2d0335f50c27fff30e27d6eaa767b5c))

## [0.3.1](https://github.com/by-openclaw/lib-opnsense/compare/v0.3.0...v0.3.1) (2026-04-08)


### Bug Fixes

* restore -blue suffix on version badge (Release Please ate it) ([63fee2c](https://github.com/by-openclaw/lib-opnsense/commit/63fee2c08a8424f925e7df2bcc4e438fa7038e97))

## [0.3.0](https://github.com/by-openclaw/lib-opnsense/compare/v0.2.0...v0.3.0) (2026-04-08)


### Features

* 4 Unbound DNS managers — host override, forward, ACL, DoT ([b883409](https://github.com/by-openclaw/lib-opnsense/commit/b883409860e455083192ab81c1ea598c7b623783))
* 5 Kea DHCP managers — dual-stack DHCPv4 + DHCPv6 ([9687db6](https://github.com/by-openclaw/lib-opnsense/commit/9687db68eb94f2b90836dd1bb65bd759282ac8d8))
* 7 extra interface managers — bridge, GIF, GRE, LAGG, loopback, neighbor, VXLAN ([1eb2add](https://github.com/by-openclaw/lib-opnsense/commit/1eb2addd0ead602e12880005ba8e7e4f9518ac0a))
* add 4 Unbound DNS managers — host override, forward, ACL, DoT ([8580ec9](https://github.com/by-openclaw/lib-opnsense/commit/8580ec93430ad5765f68847a954e0a515212d327))
* add 5 Kea DHCP managers — dual-stack DHCPv4 + DHCPv6 ([957bb26](https://github.com/by-openclaw/lib-opnsense/commit/957bb26b82d1c7e95a898400d67429ee986c6a1e))
* add 7 extra interface managers — bridge, GIF, GRE, LAGG, loopback, neighbor, VXLAN ([abaac95](https://github.com/by-openclaw/lib-opnsense/commit/abaac959e50eb555c6f5f924c1c8fba8af4f9e27))
* add FwNptManager — IPv6 Network Prefix Translation (NPTv6/NAT66) ([ef67053](https://github.com/by-openclaw/lib-opnsense/commit/ef670531eb5d6ace038e1c2976d9c59f6ad01def))
* add missing fields to FW managers — invert, gateway, categories, statetype ([231ac8c](https://github.com/by-openclaw/lib-opnsense/commit/231ac8cd23967157619b164fa6b98af7aebed8bb))
* add routing managers — RtGatewayManager + RtRouteManager ([ba075b6](https://github.com/by-openclaw/lib-opnsense/commit/ba075b609da379ff9a3c1da8b69c626913ed66ba))
* add sequence field to all FW rule managers and models ([d306847](https://github.com/by-openclaw/lib-opnsense/commit/d3068479cd014a97bd70c019c84010b73b49e720))
* add SyslogDestManager — remote syslog destinations ([1346a18](https://github.com/by-openclaw/lib-opnsense/commit/1346a184de8ca4481537f0a0a32a7a45e574e7d2))
* add TsQueueManager + TsRuleManager — complete traffic shaper domain ([f330faa](https://github.com/by-openclaw/lib-opnsense/commit/f330faa6e40340a1ae0c60f110e8f002e780d026))
* add typed frozen dataclass models for all 12 BaseManager entities ([56d8f30](https://github.com/by-openclaw/lib-opnsense/commit/56d8f303af792bb1e4da397f3843e00c1798e13c))
* add UbHostAliasManager (create+read) + UbDiagnosticsManager (read-only) ([e9d1b6e](https://github.com/by-openclaw/lib-opnsense/commit/e9d1b6e37296dfae52f04c2542c198cab0a6e742))
* add WireGuard managers — WgServerManager + WgClientManager ([2f2626b](https://github.com/by-openclaw/lib-opnsense/commit/2f2626bbb406cb372c71d5db3a9b076f37f2c318))
* FW field completeness — invert, gateway, categories, statetype (+36 fields) ([020c97e](https://github.com/by-openclaw/lib-opnsense/commit/020c97e460c10ad394b1bd20e14ac82f4a199931))
* FwNptManager — IPv6 NPTv6 (NAT66) prefix translation ([8b832e6](https://github.com/by-openclaw/lib-opnsense/commit/8b832e6b5d138df007e3c81c04a420eb2b7e1c18))
* nested dict support — Kea option_data + D-NAT source/destination ([9768125](https://github.com/by-openclaw/lib-opnsense/commit/976812582db2627180f7049b260d1fa9e28cebc3))
* nested dict support — validators, diff, Kea option_data, D-NAT source/destination ([0296319](https://github.com/by-openclaw/lib-opnsense/commit/029631995092c202b25092ec6980f16ffdc31ade))
* per-call timeout and max_retries override on all client methods ([873eb58](https://github.com/by-openclaw/lib-opnsense/commit/873eb5851b3dd92b42074c93998250e296f99307))
* per-call timeout and max_retries override on all client methods ([55e4af7](https://github.com/by-openclaw/lib-opnsense/commit/55e4af76cea4777a906cc25c65cca721d8090b7e))
* routing managers — RtGatewayManager (read-only) + RtRouteManager (CRUD disabled) ([3de092a](https://github.com/by-openclaw/lib-opnsense/commit/3de092acce78c28bbaf56fbdce560085aac263e1))
* SyslogDestManager + version badge fix + Release Please config ([896fad0](https://github.com/by-openclaw/lib-opnsense/commit/896fad06b475e6cacf568a51f9f260616200715b))
* TsQueueManager + TsRuleManager — complete traffic shaper domain ([cf43f37](https://github.com/by-openclaw/lib-opnsense/commit/cf43f378f845e812df8339fa2de4a05679c19838))
* typed frozen dataclass models for all 12 BaseManager entities ([a80e76e](https://github.com/by-openclaw/lib-opnsense/commit/a80e76e363625d3b25a169a8d50bf12d5b65706b))
* WireGuard managers — WgServer + WgClient + generate_keypair() ([7530577](https://github.com/by-openclaw/lib-opnsense/commit/75305775893cfafe09422f6d3e06a67e6ab71fd9))


### Bug Fixes

* add interface field to kea6_subnet unit test params ([515e1fd](https://github.com/by-openclaw/lib-opnsense/commit/515e1fd05f04e4ff8e7621f60776a8ce071b7306))
* add interface field to Kea6SubnetManager + DHCPv6 integration tests ([b14179f](https://github.com/by-openclaw/lib-opnsense/commit/b14179f4e434b2e89570012896be6d3216f1f144))
* add TXT record type to UbHostOverrideManager validator + model ([c0bfc4f](https://github.com/by-openclaw/lib-opnsense/commit/c0bfc4fc0d385c6575b84f0bf52e37d321ec8eff))
* remove duplicate txtdata key in ub_host_override validators ([b9caa8b](https://github.com/by-openclaw/lib-opnsense/commit/b9caa8b02b10b97cf8e00a5c3ed592cbce0e83ea))
* remove version badge (private repo, shields.io can't access) ([80f1e7d](https://github.com/by-openclaw/lib-opnsense/commit/80f1e7d3b4f61a2b8471af3c5ee52a9fd1c0c1e3))
* restore version badge + configure Release Please to update it ([4de23b8](https://github.com/by-openclaw/lib-opnsense/commit/4de23b8fe15dd698bd230acde49ef76156295c98))
* use generate_keypair() in WG integration tests + dynamic version badge ([d17a755](https://github.com/by-openclaw/lib-opnsense/commit/d17a75512fc78cd7bd21cbb05053cac0f46dfb2f))
* use Null4 blackhole gateway for route tests, not WAN_DHCP ([3a47d07](https://github.com/by-openclaw/lib-opnsense/commit/3a47d07edff61526258e4ee8c277943ea1748b0c))


### Documentation

* add api-coverage.md link to README.md and CLAUDE.md ([f99ed8c](https://github.com/by-openclaw/lib-opnsense/commit/f99ed8c9bbd2a156dfb7b24b203f1ac022cc720c))
* add INPUT/OUTPUT docstrings to all 35 managers (ADR-0029 §3.2) ([5bf4a75](https://github.com/by-openclaw/lib-opnsense/commit/5bf4a75af30b961891f1831ac817e33e94d36cca))
* add mandatory constraints to CLAUDE.md — api-coverage, integration tests, secrets ([fd33ba1](https://github.com/by-openclaw/lib-opnsense/commit/fd33ba107dddc654b80c71697b05a987b1f91b1f))
* add WireGuard key pair flow to README + api-coverage ([5b5a236](https://github.com/by-openclaw/lib-opnsense/commit/5b5a23655da5c0458f0cfcb0926c083ba1d78999))
* clarify routing test strategy in api-coverage.md ([bbe1aae](https://github.com/by-openclaw/lib-opnsense/commit/bbe1aaea4fd65741d79d9c97331a261ec92da96c))
* fix ub-host-override notes — add TXT to supported record types ([da9a072](https://github.com/by-openclaw/lib-opnsense/commit/da9a072dd332da6dac5cd1adfdab5a2ef311f2bc))
* group README managers by scope (auth, fw, if, ts, dns) ([ae9c497](https://github.com/by-openclaw/lib-opnsense/commit/ae9c4975341b377a47ea2d6f058023addb046219))
* INPUT/OUTPUT docstrings on all 35 managers (ADR-0029 §3.2) ([3127652](https://github.com/by-openclaw/lib-opnsense/commit/3127652167b30c5b3ce26613c75569bfc146efe1))
* mark Dnsmasq + DHCP Relay as SKIPPED in api-coverage.md ([2d26bf2](https://github.com/by-openclaw/lib-opnsense/commit/2d26bf293a8da6ba79cf39e9d81c0032c2454241))
* mark Dnsmasq + DHCP Relay as SKIPPED in api-coverage.md ([85831c4](https://github.com/by-openclaw/lib-opnsense/commit/85831c43d4e9efb5eee3c559d5f5041fe19fcab8))
* single source of truth — match keys + notes in api-coverage.md, summary in README ([edafac6](https://github.com/by-openclaw/lib-opnsense/commit/edafac6968b5358828036b5bb5b8e57462f6ca22))
* update api-coverage.md — 18 managers integration tested ([1b3de2a](https://github.com/by-openclaw/lib-opnsense/commit/1b3de2ae3b7572cd64f08271c1cc0dfb109b215e))
* update INPUT docstrings for nested dict fields (dnat, kea4) ([a59de84](https://github.com/by-openclaw/lib-opnsense/commit/a59de8466a8a55bdff37d7fe795643a8eb8d171d))
* update INPUT docstrings for nested dict fields (dnat, kea4) ([66445e8](https://github.com/by-openclaw/lib-opnsense/commit/66445e8e64a3de1b06b68c1212934fe870215acd))
* update README — 37 managers, all scopes listed ([603dc59](https://github.com/by-openclaw/lib-opnsense/commit/603dc596e0e96399d47610aa71885d8c2d3144e1))
* update README manager count 20 → 37 + add missing scopes ([a501e01](https://github.com/by-openclaw/lib-opnsense/commit/a501e019d93b1765ebd9fa90d8c27c869969ec29))
* update README.md and test-zone-plan for v0.2.0 + duplicate detection ([430d7d6](https://github.com/by-openclaw/lib-opnsense/commit/430d7d6b9acf052efe6bb7d6820e864802ca0e2e))
* update README.md for 20 managers + Unbound DNS + test counts ([ca73391](https://github.com/by-openclaw/lib-opnsense/commit/ca73391a7f4393b7b82ed91b2f278273a46dac6a))

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
