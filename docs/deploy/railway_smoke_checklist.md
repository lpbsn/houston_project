# Railway smoke checklist — prod-test V1

Operator checklist for **technical** post-deploy validation on Railway (or local prod-test stack for routing/PWA only).

Product journey: [`docs/qa/prod_test_smoke.md`](../qa/prod_test_smoke.md). Operator hub: [`prod_test_runbook.md`](prod_test_runbook.md).

---

## Automated readonly checks

Run from the repository root. Do **not** paste secrets into the command line or tickets.

```bash
BASE_URL=https://<railway-domain> ./scripts/smoke/readonly.sh
```

The script is the single source of truth for infra curls (health, SPA routing, API/WS not SPA, PWA manifest + service worker). See [`scripts/smoke/readonly.sh`](../../scripts/smoke/readonly.sh) for assertions and `--help`.

- [ ] `readonly.sh` exits 0 on the public origin

---

## Local prod-test (routing / PWA only)

The local stack ([`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml)) validates same-origin routing **without** `celery-worker` or `celery-beat`.

```bash
make up-prod-test
make migrate-prod-test   # first boot or after schema changes
BASE_URL=http://localhost:8080 ./scripts/smoke/readonly.sh
```

- [ ] Local `readonly.sh` passes on `http://localhost:8080`

Worker, beat, and OpenAI pipeline checks below are **Railway sign-off only** when using the local stack.

---

## Manual checks (Railway sign-off)

Complete these on the deployed Railway project. Details: [`railway_deploy_contract.md`](railway_deploy_contract.md).

### Workers

- [ ] `celery-worker` logs show worker ready (e.g. `celery@houston-worker`)
- [ ] `celery-beat` logs show scheduler running

### Bootstrap

- [ ] `import_business_unit_catalog` run after first migrate (see contract § post-migrate bootstrap)

### Media volume

- [ ] One photo uploaded via the report flow; thumbnail/read works via API (api-web volume)

If `readonly.sh` passes but observations stay `queued`, inspect worker logs first — worker down is **blocking** for prod-test.

---

## Out of scope for this checklist

- Auth/session smoke (manual login in browser or future script)
- Cache header verification (see [`railway_static_frontend.md`](railway_static_frontend.md))
- CI against live Railway
- Full product journey (see [`prod_test_smoke.md`](../qa/prod_test_smoke.md))
