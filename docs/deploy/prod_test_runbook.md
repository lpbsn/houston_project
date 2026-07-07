# Prod-test operator runbook — Railway V1

Short **operator hub** for day-0 deploy through recurring ops. Technical detail lives in PR5 docs — linked below, not duplicated here.

| Document | Role |
|---|---|
| [`railway_deploy_contract.md`](railway_deploy_contract.md) | Service topology, start commands, healthchecks, rollback |
| [`railway_variables.md`](railway_variables.md) | Variable matrix per service |
| [`infra/railway/README.md`](../../infra/railway/README.md) | Config-as-code wiring (Root Directory, Config File paths) |
| [`railway_smoke_checklist.md`](railway_smoke_checklist.md) | Technical post-deploy checklist |
| [`prod_test_smoke.md`](../qa/prod_test_smoke.md) | Product smoke on Railway (FR) |

**Merge PR6** validates docs + `readonly.sh` locally. **Railway sign-off** (real deploy, OpenAI, backups) is human, post-merge, before external pilot.

---

## 0. Local gates (before first Railway deploy)

From repo root:

```bash
make backend-check
make web-check
make backend-deploy-check
```

Optional routing/PWA check without Railway:

```bash
make up-prod-test
make migrate-prod-test   # first boot only
BASE_URL=http://localhost:8080 ./scripts/smoke/readonly.sh
```

Local prod-test has **no** celery-worker/beat — see [`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml).

---

## 1. Create Railway project

Follow [`infra/railway/README.md`](../../infra/railway/README.md):

- PostgreSQL + Redis plugins (private)
- Three app services from the same repo: `api-web`, `celery-worker`, `celery-beat`
- Root Directory `/` ; Config File paths per service table
- Variables per [`railway_variables.md`](railway_variables.md)

---

## 2. First deploy, migrate, catalog

Per [`railway_deploy_contract.md`](railway_deploy_contract.md):

- Push connected branch → Railway builds from Dockerfiles in `railway.toml`
- Migrations run via `api-web` pre-deploy command
- After first migrate, run manually once:

```bash
cd /app/apps/api && uv run python manage.py import_business_unit_catalog
```

Use Railway shell or `railway run` on `api-web`.

---

## 3. Technical smoke

Use [`railway_smoke_checklist.md`](railway_smoke_checklist.md):

```bash
BASE_URL=https://<railway-domain> ./scripts/smoke/readonly.sh
```

Then complete manual worker/beat/media checks on Railway.

---

## 4. Product smoke

Use [`prod_test_smoke.md`](../qa/prod_test_smoke.md) (French) — same journey as [`pilot_smoke_checklist.md`](../qa/pilot_smoke_checklist.md) on HTTPS same-origin, with real OpenAI.

---

## 5. Incident observability

**Logs** — Railway dashboard per service. See contract § Logs.

**Stuck or failed observation pipeline** — grep worker/api logs for:

- `observation_pipeline_failed`
- `observation_pipeline_stuck_processing`

**Processing status API** (submitter or establishment admin):

```txt
GET /api/v1/establishments/{establishment_id}/observations/{observation_id}/processing-status/
```

Never paste secrets, tokens, raw observation text, or private media paths.

---

## 6. Recurring ops

| Task | Reference |
|---|---|
| Env var change → redeploy | Contract § Restart and redeploy |
| Code rollback | Contract § Rollback (minimal) |
| Postgres backup / restore | Contract § postgres backup ; [`prod_test_decisions.md`](prod_test_decisions.md) §8 |
| Media backup | Contract § Known limitations V1 ; decisions §9 |

---

## 7. Purge test data

Destructive — use only on prod-test, not production.

1. Reset Postgres (restore empty backup or Railway plugin reset / new instance + update `POSTGRES_*` on all services)
2. Clear `private_media` on the **api-web** volume

**V1 limitation:** worker and api-web do not share a volume — cross-service media purge is not fully guaranteed. See contract § Known limitations V1 — private media.

---

## 8. Troubleshooting index

| Symptom | Where to look |
|---|---|
| Health OK but observations `queued` | Worker logs ; [`railway_smoke_checklist.md`](railway_smoke_checklist.md) § Workers |
| Blank page / wrong asset | `readonly.sh` ; contract § api-web routing |
| Deep-link 404 (SPA) | `readonly.sh` `/signals` check |
| CSRF / login loop | [`railway_variables.md`](railway_variables.md) `CSRF_TRUSTED_ORIGINS` ; [`railway_security.md`](railway_security.md) |
| Upload 413 / 400 | Contract § Upload limits ; [`prod_test_smoke.md`](../qa/prod_test_smoke.md) § Smoke négatif |
| Photo submit blocked | [`prod_test_smoke.md`](../qa/prod_test_smoke.md) § Smoke négatif (expected behaviour) |
| Signal never appears | Worker logs ; grep `observation_pipeline_failed` ; processing-status endpoint |
| WebSocket issues | Contract § WebSocket ; confirm `/ws/*` not SPA (`readonly.sh`) |
| Beat schedules missing | Beat logs ; contract § celery-beat volume |

---

## Sign-off (post-merge, not PR6 merge criteria)

Before inviting external testers, complete Railway sign-off in [`prod_test_smoke.md`](../qa/prod_test_smoke.md) plus backups and rollback readiness per contract and [`prod_test_decisions.md`](prod_test_decisions.md).
