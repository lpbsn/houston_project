# Smoke checklist

Status: authoritative  
Last reviewed: 2026-09-19

Unified smoke validation for local pilot and Railway prod-test.

## Local pilot — stack

- [ ] `.env` configured (`DJANGO_SECRET_KEY`)
- [ ] `make bootstrap-dev` OK (`catalog-check`: 14 BU, 134 subjects)
- [ ] `docker compose ps`: postgres, redis, api, celery **Up**
- [ ] Health: `curl` → `200` on http://localhost:8000/api/v1/health/
- [ ] `make web-dev` → http://localhost:5173 (no port conflict with `make up` web container)

## Local pilot — native (simulator / emulator)

Optional. Not CI. Local `make web-cap-sync` already exists. Store AAB procedure: [`native_release.md`](native_release.md). CI `cap sync` remains Capacitor Lot 11 (**deferred**).

- [ ] Xcode (iOS Simulator) and/or Android Studio (emulator) installed — see [`INSTALL_MAC.md`](../../INSTALL_MAC.md)
- [ ] iOS: `VITE_API_BASE_URL=http://localhost:8000` then `make web-cap-sync`; login + one terrain flow + WS
- [ ] Android emulator: `VITE_API_BASE_URL=http://10.0.2.2:8000` then `make web-cap-sync` (rebuild required; default `.env` `localhost` does not reach the host)
- [ ] `VITE_PUBLIC_APP_URL` (Vite) and `HOUSTON_PUBLIC_APP_URL` (Django) are distinct variables; set both to the same public HTTP(S) origin (not the emulator API host `10.0.2.2`)
- [ ] `make web-dev-native` is a compile-time pin only — it does not authenticate in the browser

## Local pilot — product journey

- [ ] Login with an existing membership, **or** grant a local Platform operator and open desktop `/platform`
- [ ] Organisation + establishment created/selected (Platform wizard, or existing membership)
- [ ] Establishment activated (Platform complete; invited Owner/Director only accept + wait)
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
- [ ] Local operator grant available if testing Platform (`grant_platform_operator`)
- [ ] `celery-worker` and `celery-beat` running (Railway logs)
- [ ] Automated: `BASE_URL=https://<domain> ./scripts/smoke/readonly.sh` exits 0

**No `make web-dev`** on Railway — frontend is same-origin HTTPS build.

## Railway prod-test — product journey

Same steps as local, URLs:

| Resource | URL |
|----------|-----|
| App | `https://<railway-domain>/` |
| Platform (desktop) | `https://<railway-domain>/platform` |
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

## Observation compose (Railway / local)

Photos stay local `File` until Envoyer (`POST temporary-uploads` then `POST observations/`). Compose remains possible while offline; Envoyer is **disabled** while offline. A failed send keeps the draft (text + local photos). Do not require photos `ready` before compose.

## References

- Daily dev: [`../engineering/local_development.md`](../engineering/local_development.md)
- Operator runbook: [`prod_test_runbook.md`](prod_test_runbook.md)
- Install Mac: [`../../INSTALL_MAC.md`](../../INSTALL_MAC.md)

## Out of scope

- Vitest / `npm test` in this checklist
- Full RBAC matrix automation
