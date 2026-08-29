# Local development

Status: authoritative  
Last reviewed: 2026-08-19

Daily workflow for Houston on macOS / OrbStack. Install from scratch: [`INSTALL_MAC.md`](../../INSTALL_MAC.md).

## Recommended stack

- **Backend:** Docker (`make up-backend`) — postgres, redis, api, celery
- **Frontend:** host npm (`make web-dev`) — http://localhost:5173

Do **not** run `make up` (Docker web on 5173) and `make web-dev` at the same time.

## First-time bootstrap

```bash
cp .env.example .env
# Edit DJANGO_SECRET_KEY, HOUSTON_REGISTRATION_INVITE_CODES
make build-backend
make bootstrap-dev
make web-install
make web-dev
```

`make bootstrap-dev` chains: `up-backend` → `migrate` → `import-catalog` → `check` → `catalog-check`.

Catalog CSV and import policy: [`docs/catalogue/README.md`](../catalogue/README.md).

Optional scheduler (action plan horizon beat): `make up-scheduler`.

After `.env` changes with stack running: `make recreate-backend` (reloads api/celery env). `make restart-backend` does **not** reload `.env`.

`make web-dev` loads `VITE_*` from the repo-root `.env` (`Vite envDir`). With `VITE_API_BASE_URL=http://localhost:8000`, the browser calls the API on `:8000` directly (CORS via `HOUSTON_CLIENT_ORIGINS`). In Web runtime, when the page and configured API hosts are the local loopbacks `localhost` and `127.0.0.1`, the client aligns the API hostname with the page hostname so `SameSite=Lax` auth cookies remain same-site. The origin allowlist alone does not make cross-site cookies attach. Leave the base URL empty to keep relative `/api` paths and the Vite proxy.

Native Capacitor (`make web-cap-sync`) copies `dist-native/` into the iOS and Android projects. `VITE_API_BASE_URL` is baked at native build time — rebuild and sync after changing it.

| Target | `VITE_API_BASE_URL` |
|--------|---------------------|
| iOS Simulator | `http://localhost:8000` (default `.env.example`) |
| Android emulator | `http://10.0.2.2:8000` then `make web-cap-sync` |
| Physical device | LAN IP or HTTPS API host (not `localhost`) |

Set `VITE_PUBLIC_APP_URL` to the public HTTP(S) origin (same value as `HOUSTON_PUBLIC_APP_URL`, no path/query/hash) so in-app invitation copy links are usable outside the WebView. Native builds require it. Native deep-link parsing is strict HTTPS against that origin.

Android handler QA (intent → app → navigation), without claiming a verified App Link:

```bash
adb shell am start -W -a android.intent.action.VIEW -d "https://app.spore-os.com/invitations/…" app.spore
```

That proves the Capacitor listener and `AppRoute` resolution. It does **not** prove Digital Asset Links. Automatic open from Chrome/email (App Links E2E) stays blocked until a real `assetlinks.json` is published. iOS Universal Links E2E stay blocked on the Apple Developer Program (same as APNs). Do not commit TEAMID or signing-fingerprint placeholders; nginx already serves `/.well-known/apple-app-site-association` and `/.well-known/assetlinks.json` as `404` (not the SPA) until those files exist.

`DJANGO_ALLOWED_HOSTS` must include `10.0.2.2` so Django accepts the emulator `Host` header. `HOUSTON_CLIENT_ORIGINS` must include `capacitor://localhost` and `https://localhost`. Debug Android allows mixed content / local cleartext only via `android/app/src/debug/` (not the committed `capacitor.config.ts`). iOS Simulator and Android emulator require Xcode / Android Studio on the machine. Native validation uses `build:native` / `cap:sync`, not the Vite `dev:native` server (`base: '/'` vs packaged `'./'`).

## Daily commands

| Task | Command |
|------|---------|
| Start backend | `make up-backend` |
| Start frontend | `make web-dev` |
| Native Vite compile-time pin (no auth) | `make web-dev-native` |
| Capacitor sync after native build | `make web-cap-sync` |
| Django shell | `make shell` |
| Migrations | `make migrate` |
| Import catalogue | `make import-catalog` |
| Verify catalogue counts | `make catalog-check` |
| Backend tests | `make test` |
| Full backend check | `make backend-check` |
| Frontend typecheck | `make web-typecheck` |
| Regenerate OpenAPI types | `make schema && make web-api-generate` |
| Full local verify | `make verify` |

## Reset DB (destructive)

Full local wipe when **no data must be retained**:

```bash
make reset-dev-db
```

Behavior: warns, then `docker compose down -v --remove-orphans`, then `make bootstrap-dev` (migrate + import catalogue + checks). Refused if `.env` points to a remote database (`assert-local-dev-db.sh`). After reset, `make web-install` if Docker web was used, then `make web-dev`.

If establishment/user data must be kept, **do not** use `reset-dev-db` — plan a backfill / data migration instead (see [`../deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md)).

### Clean operational test data (not a full reset)

```bash
make clean-operational-test-data ARGS='--dry-run'
make clean-operational-test-data ARGS='--confirm'
```

Calls `manage.py clean_operational_test_data` (local/dev only). Requires `--dry-run` or `--confirm`.

- **Deletes:** notifications, comments/mentions, observations (+ media/processing/candidates/source links), signals, action plans (templates, tasks, schedules, executions, assignees), temporary uploads, media files, analytics patterns / sightings / issue reports / pattern lifecycle events, `PointTransaction`, `BadgeAward`.
- **Preserves:** users, establishments, memberships, business units, catalog infra (`Catalog*`), chat, `ai_usage_logs`, `GamificationSeason`.
- **Cutover:** overwrites `AnalyticsHistoryCoverage.reliable_from` to the cleanup instant (lifecycle journals only). Does not insert history baselines.

Lot 5 sequence: `--dry-run` then `--confirm`, then recreate the operational loop (observations → signals → plans). Dashboard **pôle** = current `responsible_business_unit`; **localisation** = `location_text` (not `OperationalUnit`). Journal / cycle coverage can stay `partial` while the selected period starts before `history_reliable_from`. Contributors stay empty until new point awards.

## Automatic checks

| Command | Expected |
|---------|----------|
| `make catalog-check` | `14 CatalogBusinessUnit, 134 CatalogActivitySubject` |
| `make check` | Django system check OK |
| `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health/` | `200` |

## E2E product path (manual)

1. Register/login (`/onboarding` with invite code)
2. Create org + establishment, complete onboarding (`onboarding_proposal_v4`)
3. Activate establishment
4. Submit observation (optional photo)
5. Signal appears in feed (celery required)
6. Create action plan from signal
7. Execution visible in execution feed

Smoke checklist: [`../deploy/smoke_checklist.md`](../deploy/smoke_checklist.md).

## Observation pipeline

Requires `celery` service. For realistic AI in manual testing:

```env
HOUSTON_AI_OBSERVATION_PROVIDER=openai
OPENAI_API_KEY=...
```

Automated pytest uses fake provider. After env change: `make recreate-backend`.

## URLs

| Resource | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| API health | http://localhost:8000/api/v1/health/ |
| Swagger | http://localhost:8000/api/docs/ |

## Makefile reference

Run `make` from repo root. Full target list is in the root [`Makefile`](../../Makefile). Common targets: `build-backend`, `up-backend`, `up`, `up-build`, `down`, `migrate`, `import-catalog`, `catalog-check`, `bootstrap-dev`, `reset-dev-db`, `clean-operational-test-data`, `test`, `lint`, `schema`, `web-dev`, `web-test`, `verify`, `infra-check`.

## Private media

Docker uses named volume `private_media`. Local `apps/api/private_media` only for non-Docker backend or troubleshooting.
