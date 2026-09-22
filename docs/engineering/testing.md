# Houston testing conventions

Phase build: tests protect **product risk**, not line coverage or implementation details.

## Philosophy

- A test must protect a **behavior**, **business rule**, **permission**, **API contract**, or **critical regression**.
- **Check existing coverage** in the same domain and layer before adding a test — extend a focused test rather than duplicating another layer.
- **Grow by extending, not by multiplying files.** When a feature lands: find the existing invariant (permissions matrix, service test, selector, one API case, or corpus row); extend that table or corpus. Add another layer only when the new risk is distinct (HTTP shape, CSRF, after-commit, IDOR with a side effect). Do not add `test_*lot*`, `*_spike*`, a versioned golden (`*_vN_golden` beside the current apply-side corpus), or a journey that only re-proves wiring already covered.
- **Isolation is a table, not a new file per endpoint.** Cross-establishment 404/empty-list cases belong in one parametrized suite per domain. Do not re-prove `is_valid_membership` fail-closed in every app’s `test_permissions.py`.
- **Pipeline apply-side has one current corpus.** Lots are metadata on that corpus, not extra pytest modules. Keep G01–G11 / current V6 apply-side in the PR suite. Live OpenAI smokes stay opt-in.
- Prefer explicit setup over opaque fixtures.
- Do not use source inspection (`readFileSync` + `toContain`) for application behavior. Isolation tests may read committed nginx / Capacitor / Vite / package scripts when the invariant is a **deploy file** that TypeScript never executes. That is complementary to `apps/web/scripts/validate-*-build.mjs`, which assert **produced** `dist` / `dist-native` / `dist-landing` artifacts after a build. Do not use `readFileSync` to assert that a TypeScript source still contains a symbol.
- Do not chase global coverage percentages or per-file test quotas.
- Delete weak tests rather than maintaining historical noise.
- During development: run **targeted** tests (`make backend-test ARGS='…'`, `npm test -- path`); before merge: project gates (`make backend-check`, `make web-check` / `make verify`).

## Risk by layer

Add a test only when the layer owns product risk **not already asserted elsewhere**. Do not re-prove the same rule in permissions, API, hooks, and pages.

### Backend

| Layer | Test when | Avoid |
|-------|-----------|-------|
| `permissions.py` | Role×scope combinations, readable/visible rules, edge cases not trivially exposed by API | Re-testing every boolean already matriced in unit via identical API 403 cases |
| `services.py` | State transitions, invariants, DB side effects, after-commit behavior | Re-asserting permission booleans the service delegates unchanged |
| `selectors.py` | Query scoping, filtering, sorting, tenant isolation in reads | Full HTTP round-trips for pure query logic |
| `test_*_api.py` | HTTP status, response shape, CSRF, tenant isolation at the boundary | Duplicating each permission unit case as a separate API test |
| Celery / WS / producers | Side effects after commit, idempotence, payload allowlist, sensitive-data guards | Mocks that bypass transactional DB without reason |
| `models.py` | DB constraints, normalization, business invariants tied to the schema | Declarative `_meta` (verbose names, ordering) with no runtime behavior |
| Journey / integration | Cross-app product loop (e.g. observation → pipeline → signal feed) when fragmented unit tests miss wiring | Replacing focused unit/API tests with one mega-test |

Shared helpers live in `houston/testing/` or domain `tests/helpers.py` — **never** import from `test_*.py` modules.

### Frontend

| Layer | Test when | Avoid |
|-------|-----------|-------|
| `features/*/lib/*.test.ts` | Algorithms, validation, cache keys, navigation derivation, RBAC display hints | — |
| Hooks / mutations (jsdom) | TanStack Query invalidation, mutation error paths, realtime wiring with real `QueryClient` | Mocking everything except the API boundary |
| Pages / components | Wiring at product risk: auth purge, establishment switch cache, navigation guards, blocked submission | Exact Tailwind classes, French copy, shadcn primitive styling |
| Auth provider | `purgeNonAuthQueries` / `clearAuthenticatedQueryCache` on logout, login, registration, establishment switch | Re-testing query-invalidation lib rules already covered in `query-invalidation.test.ts` |

Reference implementations: `query-invalidation.test.ts`, `auth-provider.test.tsx`.

## Backend (pytest)

### Commands

```bash
# Canonical (Docker stack, local DB only)
make test
make backend-test

# Targeted (preferred while iterating)
make backend-test ARGS='houston/signals/tests/test_pipeline_v4_golden.py -q'
make backend-test ARGS='houston/signals/tests/test_pipeline_v4_golden.py::test_golden_case -q'

# Lint (Docker)
make backend-lint
make lint

# Profile slow tests (diagnostic — see baseline below)
docker compose exec api sh -lc 'cd /app/apps/api && uv run pytest --durations=50 -q'

# Reproduce CI backend test env locally (DJANGO_DEBUG=0, production throttle rates)
make backend-test-ci

# Heavy suite (Konoha replay and other measured `heavy` tests; not a PR gate)
make backend-test-heavy
```

Do not run `cd apps/api && uv run pytest` on the host — use Make targets or `docker compose exec api`.

### Layout

- Domain tests live in `houston/<domain>/tests/`.
- Shared factories and auth helpers live in `houston/testing/`:
  - `factories.py` — memberships, establishments, users
  - `auth.py` — `login`, `auth_headers`, `build_api_membership`, `TEST_PASSWORD`
  - `taxonomy.py` — business units, activity subjects, restaurant v3 taxonomy
  - `onboarding.py` — manual V2 payloads and onboarding session helpers
  - `pipeline.py` — observation/golden pipeline helpers
- Domain-specific shared helpers: `tests/helpers.py`, `tests/ws_helpers.py`, `tests/pipeline_helpers.py`, etc. — import these, not `test_*.py`.
- Catalog fixtures in `establishments/tests/conftest.py`:
  - `imported_catalog` — function-scoped sync via `sync_catalog_from_normalized_rows()` (**do not change** scope or seed strategy for taxonomy contraction work)
  - `requires_empty_catalog` — assert no catalog rows (tests that expect an empty DB)
- **Do not** widen `imported_catalog` to session scope without a measured pilot on a single file; shared catalog state breaks isolation and blocks xdist.
- **Taxonomy contraction / env reset:** when an environment has **no data to retain**, prefer a full DB reset + migrate + `make import-catalog` (local: `make reset-dev-db`) over a complex business backfill. When data **must** be retained, **do not reset** — plan an explicit backfill / data migration. Operator order: [`../deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md).

### Markers

| Marker | Meaning | CI PR |
|--------|---------|-------|
| *(none)* | Standard fake-provider suite | Yes |
| `slow` | Reserved — requires **explicit justification** in code review: real sleep, sustained >1s runtime, live external API, or heavy concurrency | No (excluded via Makefile/CI filter) |
| `heavy` | Measured dataset / catalog-mass / demo-replay cost that is not a runtime user invariant (e.g. Konoha replay). Requires `--durations` evidence. **Do not** mark apply-side pipeline goldens G01–G11 or V6 acceptance that guard aggregation. | No (excluded via Makefile/CI filter; run with `make backend-test-heavy` or drop `-m`) |
| `openai_observation_smoke` | Live OpenAI observation pipeline; env `HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1` | No |
| `openai_smoke` | Reserved onboarding live smoke; env `HOUSTON_RUN_OPENAI_SMOKE_TEST=1` — **no tests yet** | No |
| `openai_transcription_smoke` | Reserved transcription live smoke — **no tests yet** | No |
| `auth_throttle` | Real rate-limit behavior (429); excluded from relaxed-throttle autouse fixture | Yes (when not also `slow` / `heavy`) |

#### Fake provider vs live smoke (do not conflate)

| Category | Provider | CI PR |
|----------|----------|-------|
| **Standard suite** (PR filter; ~2 900 collected functions as of the backend test-strategy audit) | `FakeObservationPipelineProvider` via autouse `force_fake_observation_pipeline_provider` | Yes |
| **Provider guard tests** | Fake + mocked OpenAI client (`test_observation_pipeline_provider.py`) | Yes |
| **Pipeline validation / golden** | Fake provider, DB-heavy | Yes (in PR) |
| **Live OpenAI smoke** | Real OpenAI (`test_openai_observation_pipeline_v6_contract_smoke.py`, `test_openai_observation_pipeline_v6_business_smoke.py`) | No — manual / pre-release only; optional local archives under `.artifacts/pipeline-v6-smoke/` (gitignored, not source of truth) |

PR filter (Makefile + CI — keep the two strings identical): `-m "not openai_observation_smoke and not openai_smoke and not slow and not heavy"`.

### Auth throttling in pytest

CI runs with `DJANGO_DEBUG=0`, which enables production auth throttle quotas and Redis-backed counters. The standard test suite calls `/auth/login/` hundreds of times from the same IP, so unguarded runs hit 429 and cascade into auth/RBAC failures.

`houston/conftest.py` applies an autouse fixture (`relaxed_auth_throttling_for_standard_tests`) for all tests **except** those marked `auth_throttle`:

- LocMem cache with a unique `LOCATION` per test
- relaxed quotas (`1000/minute`, mirroring DEBUG settings)
- skip via `yield; return` when `@pytest.mark.auth_throttle` is present (never bare `return` in this yield fixture)

Dedicated throttle tests (`test_auth_throttling_api.py`, invitation accept over-limit, etc.) must use `@pytest.mark.auth_throttle` and their own low-rate cache isolation. Production rates in `config/settings.py` are unchanged.

### Product priorities (must stay covered)

- Auth / bootstrap / CSRF / refresh rotation
- RBAC and cross-establishment isolation
- Signal lifecycle (pipeline golden G01–G11 apply-side against runtime schema/prompt `ai_observation_pipeline_v6` / `v6_2` + V6 acceptance corpus S15 / truth tables + cancel/resolve)
- Action Plan lifecycle (catalog, planning-submit, executions, schedules, service + API transitions + permissions)
- Chat WS ticket auth and message delivery
- Upload validators
- Observation → signal feed journey (`observations/tests/test_observation_signal_feed_journey.py`)
- TanStack Query cache purge on auth/session changes

### Voluntary debt

- `provisioning` — no tests until product risk is defined
- `organizations` — minimal model coverage only
- Non-critical UI pages — no page tests unless wiring is product-critical
- Playwright is not in this repository and is not a PR CI gate.

## Frontend (Vitest)

### Commands

```bash
make web-test
make web-lint
make web-typecheck
make web-build

cd apps/web && npm test
cd apps/web && npm test -- src/features/auth/pages/select-establishment-page.test.tsx
cd apps/web && npm run lint
cd apps/web && npm run typecheck
```

### Layout

- Pure lib helpers: `features/<domain>/lib/*.test.ts` (Node environment)
- Provider/hook integration: `// @vitest-environment jsdom` + `@testing-library/react`
- Shared harness: `src/test-utils/` exports `createTestQueryClient` only. Auth and WebSocket mocks stay local to the tests that need them.

### Rules

- Lib tests stay in **Node** (fast, no DOM).
- Auth provider uses **jsdom** (app `queryClient`). TanStack Query mutations use **jsdom** + `createTestQueryClient`. WebSocket hooks use **jsdom** with local mocks.
- Do not wait on real time for WebSocket auth timeout or reconnect. Use `vi.useFakeTimers()` and `vi.advanceTimersByTimeAsync` in the chat/operational WS hook tests. Presence intervals can use `vi.advanceTimersByTime` (`use-chat-conversation-presence.test.ts`). Do not raise the global `testTimeout` to absorb load.
- Do not assert exact Tailwind classes, shadcn primitive styling, or decorative/marketing French copy. Keep copy that **is** the product contract (permission denial, destructive confirmation, legal obligation, error that blocks a critical action), even without a dedicated lib constant. Shell overflow / safe-area contracts already justified in `TerrainShell` tests may assert classes when behavior (scroll, focus) is not enough.
- Do not add page tests for layout or copy when the rule already lives in lib/hook tests.
- Test files are excluded from `tsconfig.app.json`. `tsconfig.vitest.json` sets `noCheck: true` because a full test typecheck currently reports ~150 diagnostics, mostly partial mocks (`TS2345`/`TS2556` spread/callback arity) and incomplete fixtures (`TS2353`/`TS2739`), not a small set of real call-site errors. Do not add `vitest --typecheck` beside `tsc -b`.

## CI vs local gates

GitHub Actions (`.github/workflows/ci.yml`):

- **Triggers**: `pull_request` on all branches; `push` on `main` only (avoids double runs when a PR branch pushes).
- **Concurrency**: `cancel-in-progress` per ref.
- **Path filters**: backend / frontend / docs jobs run only when relevant paths change; changes to API schema sources or `schema.yml` / `types.ts` still run **both** backend and frontend jobs.

| Job | Steps |
|-----|-------|
| `backend-tests` | Django check, deploy check, migrations, ruff, OpenAPI regen + diff, pytest (PostgreSQL + Redis; smoke/slow/heavy excluded) |
| `frontend-tests` | `npm ci`, `api:generate` + diff, lint, vitest, `typecheck` (`tsc -b` once), `build:bundle` and `build:native:bundle` (vite only — no second `tsc -b`) |
| `docs-check` | `scripts/docs_check.py`, `scripts/agent_config_check.py` |

**Runtime note:** CI backend steps run **native `uv`** with GitHub Actions Postgres/Redis services. Local backend validation uses **Make/Docker only** (`make backend-check`, `make verify`) — do not run `cd apps/api && uv run …` on the host. Frontend checks may run natively from `apps/web` or via `make web-*`.

`make web-check` matches the **validations** of `frontend-tests`: lint, vitest, `tsc -b` once (`web-typecheck`), web bundle via `npm run build:bundle` (no second `tsc`), native bundle (`web-build-native-check`), `web-api-generate-check`. Standalone `make web-build` still runs `npm run build` (`tsc -b` + vite) for a full local production build.

### Local validation targets

| Target | What it runs |
|--------|----------------|
| `make backend-test-ci` | Same pytest filter as PR, with `DJANGO_DEBUG=0` (production throttle/cache baseline) |
| `make backend-test-heavy` | `heavy` tests only (Konoha replay); not a PR gate |
| `make backend-deploy-check` | `manage.py check --deploy` with CI-equivalent env — **CI runs this; `backend-check` does not** |
| `make backend-check` | Django check, ruff, migrations check, schema diff, pytest (PR marker filter) |
| `make web-api-generate-check` | regen `types.ts` from committed `schema.yml` + `git diff` |
| `make web-check` | lint, vitest, typecheck once, `build:bundle`, native bundle with placeholder `VITE_API_BASE_URL` and `VITE_PUBLIC_APP_URL` (`web-build-native-check`), `web-api-generate-check` |
| `make local-check` | `backend-check` + `web-check` |
| `make verify` | alias for `local-check` |
| `make docs-check` | `scripts/docs_check.py` + `scripts/agent_config_check.py` |
| `make agent-config-check` | `.cursor` / `.agents` structural invariants |
| `make agent-config-sync` | copy canonical `.cursor` commands/rules/skills → `.agents` |

Run `make verify` before merging when the Docker stack is up and you need full confidence. For day-to-day backend work, `make backend-test` or `make backend-lint` is enough.

Profiling: `--durations=50` and optional local Vitest JSON under `.artifacts/` — **no arbitrary duration quotas**; optimize only measured bottlenecks.

Protected areas (do not weaken): auth/CSRF/throttle, tenant isolation, pipeline golden (apply-side G01–G11 vs current V6 runtime — not an alternate AI pipeline), issue-focus aggregation, fake OpenAI guards, notification producers, query invalidation parity.

## Issue focus aggregation eval

```bash
# Live OpenAI corpus diff (opt-in, not CI)
export HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1
docker compose exec api uv run python manage.py evaluate_observation_pipeline --case-id G01 --case-id G03
docker compose exec api uv run python manage.py evaluate_observation_pipeline --json --fail-on-diff

# Plumbing check without OpenAI
docker compose exec api uv run python manage.py evaluate_observation_pipeline --provider fake --case-id G01

# S15 acceptance vs V6 runtime (fake fixtures independent of expected_v6)
docker compose exec api uv run python manage.py evaluate_observation_pipeline_v6 --fail-on-diff
docker compose exec api uv run python manage.py evaluate_observation_pipeline_v6 --json --case-id S15-12

# DB aggregation metrics (pilot monitoring)
docker compose exec api uv run python manage.py report_issue_focus_aggregation_eval --json
make backend-test ARGS='houston/signals/tests/test_pipeline_v4_golden.py houston/signals/tests/test_pipeline_v6_lot10_eval.py houston/signals/tests/test_aggregation_eval.py houston/signals/tests/test_evaluate_observation_pipeline.py -q'
```

Command: `report_issue_focus_aggregation_eval` (see `houston/signals/management/commands/`).

## Agent workflow

- Before adding or expanding tests: read this doc. For the current change, use [`test-review`](../../.cursor/commands/test-review.md).
- Nested `AGENTS.md` files hold only short layer-ownership pointers; this document is the testing procedure.
