## Summary

<!-- One sentence: what changed and why. -->

Closes #

## Type

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] chore — maintenance, refactor, CI
- [ ] security — security fix or hardening

## Files changed

<!-- List every file touched. One row per file. -->

| File | Type | Change |
|------|------|--------|
| `src/opnsense/managers/example.py` | new | ExampleManager (N lines) |
| `tests/unit/test_example.py` | new | N tests (N lines) |

## Endpoints covered

<!-- For each API endpoint this PR touches. -->

| Endpoint | Method | Tested |
|----------|--------|--------|
| `/api/domain/action` | POST | unit + integration |

## Test results

<!-- One row per test file. Full suite row mandatory. -->

| Suite | Scope | File | Passed | Failed |
|-------|-------|------|--------|--------|
| Unit | ManagerName | `tests/unit/test_manager.py` | 0 | 0 |
| Integration | Domain | `tests/integration/test_lifecycle.py` | 0 | 0 |
| **Full suite** | **All** | `tests/unit/` | **0** | **0** |
| Lint | ruff check + format | `src/` + `tests/` | clean | — |

## Safety

<!-- What is safe to touch on the live device? What is read-only? -->

- **READ-ONLY:**
- **CRUD safe (inttest- prefix):**
- **DISABLED only:**

## How to review

1. Read manager code — verify endpoint URLs, payload key, match key
2. Read unit tests — verify all CRUD + error paths covered
3. Read integration tests — verify safety boundaries respected
4. Check: no hardcoded IPs, no real domains, inttest- prefix everywhere

## Checklist

### Quality
- [ ] Lint clean (`ruff check` + `ruff format --check`)
- [ ] Type check clean (`mypy`)
- [ ] Unit tests pass
- [ ] Integration tests pass (if touching live device)
- [ ] No coverage drop

### Security
- [ ] No secrets, tokens, or passwords in committed files
- [ ] No `<REDACTED>` in code (docs only)

### Docs
- [ ] CHANGELOG entry added (if user-facing change)
- [ ] CLAUDE.md updated (if repo state changed)
- [ ] `docs/api-coverage.md` updated (if manager added/tested)

### ADR compliance
- [ ] `ensure()` returns `EnsureResult` with correct action
- [ ] `check_mode=True` tested
- [ ] Error handling: create/delete failure logged + re-raised (ADR-0029)
- [ ] Running twice produces same result (idempotent)

## Review

- [ ] @yboujraf approved

<!--
Merge rules (ADR-0019):
- Agents open PRs, never merge
- @yboujraf is sole merge authority
- No force-push to main — ever
-->
