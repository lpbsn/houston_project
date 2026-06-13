# Phase 4 — AI Observation Pipeline + Signal Feed + Signal Detail

Status: **implemented** (reference)  
Last reviewed: 2026-06-13

## Scope

- Observation → AI pipeline v4 → persisted `CandidateSignal` → validated `Signal` (create or aggregate).
- Signal Feed (`view_mode=personal|general`) and Signal Detail.
- Commands: pin, unpin, set urgency, resolve, cancel.
- **No** manual Signal CRUD; **no** feed subscription model in Phase 4 (deferred — future BU-only, then ActivitySubject subscribe/unsubscribe).

## Ma vue feed filter

- **Owner/Director** (`personal`): all active establishment Signals.
- **Manager/Staff** (`personal`): active Signals matching `MembershipScope` (BusinessUnit).
- **General**: all active establishment Signals for any active member.
- Empty personal list when manager/staff has no scopes (not an error).

## API (canonical paths)

| Method | Path |
| --- | --- |
| GET | `/api/v1/establishments/{establishment_id}/signal-feed/?view_mode=personal\|general` |
| GET | `/api/v1/establishments/{establishment_id}/signals/{signal_id}/` |
| POST | `/api/v1/establishments/{establishment_id}/signals/{signal_id}/pin/` |
| POST | `/api/v1/establishments/{establishment_id}/signals/{signal_id}/unpin/` |
| PATCH | `/api/v1/establishments/{establishment_id}/signals/{signal_id}/urgency/` |
| POST | `/api/v1/establishments/{establishment_id}/signals/{signal_id}/resolve/` |
| POST | `/api/v1/establishments/{establishment_id}/signals/{signal_id}/cancel/` |

Still out of scope / candidate: manual Signal CRUD, archive, comments, actions (Phase 5), realtime, notifications, advanced feed filters.

## Transaction rules

- `submit_observation` enqueues Celery **only** via `transaction.on_commit`.
- Pipeline aggregation uses `transaction.atomic` + `select_for_update` on matching active Signals.
- One atomic batch per observation processing; no partial Signal state on failure.

## Failure modes

| Case | ObservationProcessing | Signals |
| --- | --- | --- |
| Provider retryable error | `retrying` | none |
| Provider/schema final failure | `failed` | none |
| All candidates rejected | `processed`, `no_signal_created` | none |
| Success | `processed`, `signals_created` / `signal_aggregated` | created/updated |

## Environment (server-only)

| Variable | Default | Notes |
| --- | --- | --- |
| `HOUSTON_AI_OBSERVATION_PROVIDER` | `openai` (runtime default) | `fake` in pytest (autouse); optional `fake` in `.env` only for mechanical local runs |
| `HOUSTON_AI_OBSERVATION_MODEL` | `gpt-4.1-mini` | OpenAI model when provider is `openai` |
| `HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS` | `30` | Request timeout |
| `HOUSTON_AI_OBSERVATION_MAX_RETRIES` | `2` | Provider retries |
| `HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST` | unset | Set to `1` for opt-in live smoke pytest |

See repository `.env.example`.

## Celery (local dev)

Dedicated Compose service `celery` (same image and env as `api`):

```bash
docker compose up -d api celery
```

Requires `CELERY_BROKER_URL` (Redis). Without the worker, observations remain `queued`.

After `.env` changes:

```bash
docker compose up -d --force-recreate api celery
```

## OpenAPI

```bash
cd apps/api && uv run python manage.py spectacular --file schema.yml
cd apps/web && npm run api:generate
```

## Tests

- Pytest autouse sets `HOUSTON_AI_OBSERVATION_PROVIDER=fake` (no live OpenAI in CI). A conftest guard fails standard tests if `OpenAIObservationPipelineProvider.propose` is called accidentally.
- Manual Signaler validation requires `HOUSTON_AI_OBSERVATION_PROVIDER=openai` and `OPENAI_API_KEY`. The fake provider validates pipeline mechanics only and may produce generic titles such as "Structured issue" — do not use it to judge real-world observation understanding.
- After `.env` changes, recreate API and worker: `docker compose up -d --force-recreate api celery`.
- Contract tests: no `raw_text` in feed/detail; no manual Signal CRUD; pin/unpin/urgency permission matrix.
- Optional live smoke (not CI standard): `@pytest.mark.openai_observation_smoke` — set `HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1` and `OPENAI_API_KEY`. Live, potentially costly, slow, and non-deterministic.

## Manual Signaler validation (golden scenario)

Establishment runtime taxonomy must include at minimum (BusinessUnit / ActivitySubject):

- `restaurant` (dedicated) + transversal `maintenance` with activity subject for lighting/electrical work
- `bar` (dedicated) with `stock` (or equivalent) activity subject under `bar`

Observation text:

```text
La lumière clignote à l'entrée de restaurant. Il n'y a plus de sirop mojito au bar.
```

Expected: 2 CandidateSignals → 2 Signals (distinct BU/AS classifications), 2 `SignalSourceObservation`, general feed shows 2 cards, personal feed filtered by `MembershipScope`, post-submit popup lists count + BusinessUnit/ActivitySubject per Signal (CTA to `/signals` only, no detail redirect).

Check `AIUsageLog.provider=openai`, `status=succeeded`, empty `error_code` when using OpenAI in manual runs.

## Diagnostic commands

Dump the active runtime classification for an establishment (BusinessUnit → ActivitySubject, plus establishment-level `OperationalUnit` rows). Units are orthogonal to BU/AS classification.

```bash
cd apps/api && uv run python manage.py dump_establishment_taxonomy <establishment_uuid>
cd apps/api && uv run python manage.py dump_establishment_taxonomy <establishment_uuid> --json
```

- Default filter: `active=True` on business units, activity subjects, and operational units.
- Exit code `1` if the establishment UUID is invalid or not found.
- Use before manual Signaler validation to confirm runtime keys match the golden scenario above.
