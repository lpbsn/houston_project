# GitHub Actions CI step durations (Lot 1 baseline)

Source: `gh run view 29397589248` — workflow `CI`, branche `main`, push « logo maj », 2026-07-15T07:30:42Z  
Durée totale run: **11m28s** (rapport `gh run list`)

## backend-tests

| Step | Début (UTC) | Fin (UTC) | Durée approx. |
|------|-------------|-----------|---------------|
| Initialize containers | 07:30:49 | 07:31:13 | **24s** |
| Install backend dependencies | 07:31:17 | 07:31:20 | 3s |
| Django system check | 07:31:20 | 07:31:23 | 3s |
| Django deploy check | 07:31:23 | 07:31:24 | 1s |
| Check migrations | 07:31:24 | 07:31:25 | 1s |
| Lint backend | 07:31:25 | 07:31:25 | <1s |
| Generate OpenAPI schema | 07:31:25 | 07:31:26 | 1s |
| Verify schema.yml | 07:31:26 | 07:31:26 | <1s |
| **Run backend tests** | 07:31:26 | 07:42:05 | **10m39s** |
| Stop containers | 07:42:06 | 07:42:06 | <1s |

## frontend-tests

| Step | Début (UTC) | Fin (UTC) | Durée approx. |
|------|-------------|-----------|---------------|
| Install frontend dependencies | 07:30:52 | 07:31:03 | 11s |
| Generate frontend API types | 07:31:03 | 07:31:04 | 1s |
| Verify types.ts | 07:31:04 | 07:31:04 | <1s |
| Lint frontend | 07:31:04 | 07:31:16 | **12s** |
| **Run frontend tests** | 07:31:16 | 07:32:17 | **61s** |
| Typecheck frontend | 07:32:17 | 07:32:25 | **8s** |
| Build frontend | 07:32:25 | 07:32:34 | **9s** |

## docs-check

| Step | Durée approx. |
|------|---------------|
| Documentation drift check + Agent config check | **<1s** total |

## Constats

- Step dominant backend: **pytest** (~94 % du temps job backend-tests hors init containers).
- Step dominant frontend: **vitest** (~76 % du temps job frontend-tests hors install).
- **Double `tsc -b`** observable: typecheck (8s) + build inclut `tsc -b` (9s) — total ~17s compilation TS sur ce run.
- Jobs parallèles: backend, frontend, docs-check démarrent ensemble ; chemin critique wall-clock ≈ max(backend) ≈ **~11m**.

## Limite

Mesure ponctuelle d'un run `main` ; pas de médiane sur N runs. Variabilité runners GitHub non quantifiée.
