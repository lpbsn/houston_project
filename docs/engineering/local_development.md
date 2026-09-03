# Local development

Status: authoritative  
Last reviewed: 2026-09-03

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

Native Capacitor (`make web-cap-sync`) copies `dist-native/` into the iOS and Android projects. `VITE_API_BASE_URL` is baked at native build time — rebuild and sync after changing it. Store / Play AAB builds must not use this daily target: [`docs/deploy/native_release.md`](../deploy/native_release.md) (`make web-cap-sync-release`).

| Target | `VITE_API_BASE_URL` |
|--------|---------------------|
| iOS Simulator | `http://localhost:8000` (default `.env.example`) |
| Android emulator | `http://10.0.2.2:8000` then `make web-cap-sync` |
| Physical device | LAN IP or HTTPS API host (not `localhost`) |

Set `VITE_PUBLIC_APP_URL` to the public HTTP(S) origin (same value as `HOUSTON_PUBLIC_APP_URL`, no path/query/hash) so in-app invitation copy links are usable outside the WebView. Native builds require it. Native deep-link parsing is strict HTTPS against that origin.

Android **handler** QA (intent → app → navigation). This is the Native deep-link socle; it does **not** prove Play/Apple website association:

```bash
adb shell am start -W -a android.intent.action.VIEW -d "https://app.spore-os.com/invitations/…" app.spore
```

Association files are served from the **web** deploy (`apps/web/public/.well-known/` → Vite `dist/` → nginx), not from the Capacitor bundle. Until store identities exist, nginx must return **404** (not the SPA) for:

- `https://app.spore-os.com/.well-known/assetlinks.json`
- `https://app.spore-os.com/.well-known/apple-app-site-association`

That 404 is expected. Do **not** commit placeholder fingerprints, `TEAMID`, or a Personal Team AASA. A 200 with fake statements is worse than 404.

`pm get-app-links app.spore` **verified** only matches the certificate of the **installed** binary to `assetlinks.json`. Play-distributed builds use Play App Signing certificate(s), not the local upload key. Upload-key SHA-256 is optional later for a sideloaded Release; it is not the Play App Links target. iOS Universal Links wait on the App Store Team ID (not the Personal Team in Xcode today). Details: [`docs/deploy/native_release.md`](../deploy/native_release.md).

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

### Provision KONOHA dataset actors (not operational data)

```bash
make provision-konoha-dataset-actors ARGS='--dry-run'
make provision-konoha-dataset-actors ARGS='--confirm'
```

Calls `manage.py provision_konoha_dataset_actors` (local/dev only). Requires `--dry-run` or `--confirm`. Invites the missing ANBU + AKATSUKI manager/staff seats via the product invite/reinvite/accept path (Naruto owner, unchanged). Does **not** create observations, signals, or plans.

The versioned observation corpus lives in `apps/api/houston/establishments/data/konoha_anbu_observations.json` and `konoha_akatsuki_observations.json` (`schema_version` `konoha_dataset_observations_v1`). Human scenario tables are in [`docs/datasets/konoha/`](../datasets/konoha/). The JSON is the machine source of truth. Static validation is `validate_konoha_dataset_observations()` — it does **not** call `submit_observation`, write Signals, or log `raw_text`. Instance `routing_key` values are not stored; replay remaps them from catalogue keys + pole `specific_name`.

### KONOHA dataset replay

```bash
make clean-operational-test-data
make provision-konoha-dataset-actors ARGS='--confirm'
make provision-konoha-dataset-replay ARGS='--dry-run'
make provision-konoha-dataset-replay ARGS='--confirm'
make provision-konoha-dataset-replay ARGS='--confirm --resume'
```

Calls `manage.py replay_konoha_dataset_observations` (local/dev only). Requires `--dry-run` or `--confirm`. Replays the corpus through `submit_observation` + `run_observation_pipeline` with deterministic candidates, then product writers for qualification, resolution requests, `mark_signal_interesting`, ActionPlan cycles (`create_action_plan_with_execution` with `end_at` / `deadline_at`), execution transitions, or `resolve_signal` (manual after RR reject, otherwise Naruto owner). Comments/Mentions are out of the KONOHA replay. Do **not** write `AnalyticsHistoryCoverage.reliable_from`. A first pass wipes ANBU/AKATSUKI `GamificationSeason` rows and their point ledger so historical transitions can open months in order; `--resume` skips an event only when that writer’s fingerprint is already persisted at the same instant. A full MATCH resume is a no-op on KONOHA seasons and the point ledger. If `--resume` still has remaining events **and** KONOHA seasons exist after that remaining month, replay fail-fasts (`KonohaDatasetReplayError`) — run operational clean then `--confirm`; it does not prune or rebuild the ledger. `make clean-operational-test-data` is **required** before the first `--confirm` after switching from an observations-only replay: leftover manual resolves are incompatible with `linked_plan` groups. The command does not wipe operational observations/signals itself.

After a validated `clean` + `--confirm` + `--resume`, restore Analytics coverage to the corpus start **outside** replay:

```python
from houston.analytics.cutover import reset_history_reliable_from
from houston.analytics.models import AnalyticsHistoryCoverage
from houston.establishments.konoha_dataset_observations import OCCURRED_AT_MIN

reset_history_reliable_from(now=OCCURRED_AT_MIN)
assert AnalyticsHistoryCoverage.objects.get().reliable_from == OCCURRED_AT_MIN
```

Clean still resets `reliable_from` to `timezone.now()`; replay never writes it.

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

Run `make` from repo root. Full target list is in the root [`Makefile`](../../Makefile). Common targets: `build-backend`, `up-backend`, `up`, `up-build`, `down`, `migrate`, `import-catalog`, `catalog-check`, `bootstrap-dev`, `reset-dev-db`, `clean-operational-test-data`, `provision-konoha-dataset-actors`, `provision-konoha-dataset-replay`, `test`, `lint`, `schema`, `web-dev`, `web-test`, `verify`, `infra-check`.

## Private media

Docker uses named volume `private_media`. Local `apps/api/private_media` only for non-Docker backend or troubleshooting.
