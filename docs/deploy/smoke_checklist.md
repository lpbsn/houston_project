# Smoke checklist

Status: authoritative  
Last reviewed: 2026-07-13

Unified smoke validation for local pilot and Railway prod-test.

## Local pilot — stack

- [ ] `.env` configured (`DJANGO_SECRET_KEY`, `HOUSTON_REGISTRATION_INVITE_CODES`)
- [ ] `make bootstrap-dev` OK (`catalog-check`: 14 BU, 134 subjects)
- [ ] `docker compose ps`: postgres, redis, api, celery **Up**
- [ ] Health: `curl` → `200` on http://localhost:8000/api/v1/health/
- [ ] `make web-dev` → http://localhost:5173 (no port conflict with `make up` web container)

## Local pilot — product journey

- [ ] Register `/onboarding` with invite code (or login)
- [ ] Organisation + establishment created/selected
- [ ] Onboarding manual v2 completed, establishment activated
- [ ] Observation submitted (photo optional)
- [ ] Processing completes → signal in `/signals` feed
- [ ] Action plan created from signal
- [ ] Execution visible in `/execution` feed

## Workers & AI (local)

- [ ] `celery` running (observations stay `queued` otherwise)
- [ ] Optional: `make up-scheduler` for action plan horizon beat
- [ ] Optional: `OPENAI_API_KEY` + `HOUSTON_AI_OBSERVATION_PROVIDER=openai` for realistic signals

## Railway prod-test — preparation

- [ ] Variables per [`railway_variables.md`](railway_variables.md) and [`.env.prod-test.example`](../../.env.prod-test.example)
- [ ] `HOUSTON_REGISTRATION_INVITE_CODES` set
- [ ] `celery-worker` and `celery-beat` running (Railway logs)
- [ ] Automated: `BASE_URL=https://<domain> ./scripts/smoke/readonly.sh` exits 0

**No `make web-dev`** on Railway — frontend is same-origin HTTPS build.

## Railway prod-test — product journey

Same steps as local, URLs:

| Resource | URL |
|----------|-----|
| App | `https://<railway-domain>/` |
| Onboarding | `https://<railway-domain>/onboarding` |
| Health | `https://<railway-domain>/api/v1/health/` |

## Railway — technical manual checks

- [ ] Worker logs show ready
- [ ] Beat logs show scheduler
- [ ] Catalog import after first migrate (see [`railway_deploy_contract.md`](railway_deploy_contract.md))
- [ ] Photo upload + authorized read via API

Local prod-test routing only:

```bash
make up-prod-test
make migrate-prod-test
BASE_URL=http://localhost:8080 ./scripts/smoke/readonly.sh
```

## Photo submit guard (Railway)

Report page requires all attached photos `ready` before submit. Verify: invalid file → error; `uploading` / `failed` → submit disabled.

## References

- Daily dev: [`../engineering/local_development.md`](../engineering/local_development.md)
- Operator runbook: [`prod_test_runbook.md`](prod_test_runbook.md)
- Install Mac: [`../../INSTALL_MAC.md`](../../INSTALL_MAC.md)

## Out of scope

- Vitest / `npm test` in this checklist
- Full RBAC matrix automation
