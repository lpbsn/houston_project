# Issue focus aggregation evaluation — Lot 5

Status: **evaluation framework** (no architecture change)  
Last reviewed: 2026-06-13

## Purpose

Measure whether pipeline v4 `issue_focus` aggregation exhibits **significant under-aggregation** in real usage before considering Lot 4bis (aliases, canonical entity, etc.).

**Working hypothesis:** taxonomy + `issue_focus` remains the reference design until this evaluation demonstrates a significant problem.

## What is instrumented

### Runtime logs (apply-side)

Each pipeline candidate apply emits `observation_pipeline_candidate_applied` with:

| Field | Meaning |
| --- | --- |
| `aggregation_key` | Full 5-tuple key incl. normalized `issue_focus` |
| `taxonomy_bucket_key` | Taxonomy quadruplet without `issue_focus` |
| `issue_focus` | Normalized focus used for matching |
| `active_taxonomy_peer_count` | On **create** only: count of other active Signals same taxonomy, different focus |
| `hint_rejected_reason` | e.g. `hint_issue_focus_mismatch` when LLM hint rejected |

Source: [`apps/api/houston/core/observability.py`](../../apps/api/houston/core/observability.py), [`apps/api/houston/signals/services.py`](../../apps/api/houston/signals/services.py).

### DB report command

```bash
docker compose exec api uv run python manage.py report_issue_focus_aggregation_eval
docker compose exec api uv run python manage.py report_issue_focus_aggregation_eval --establishment-id=<uuid> --json
```

Metrics computed in [`apps/api/houston/signals/aggregation_eval.py`](../../apps/api/houston/signals/aggregation_eval.py):

| Metric | Detects |
| --- | --- |
| `taxonomy_duplicate_group_count` | Active Signals sharing taxonomy quadruplet with multiple distinct `issue_focus` values |
| `hint_issue_focus_mismatch_count` | Candidates with aggregate hint where focus differs from hint target |
| `hint_rejected_created_count` | Candidates with hint that still created a new Signal |
| `lot4bis_trigger_indicators` | Boolean flags against default thresholds (calibrate on pilot) |

## Golden baseline (documented behavior, not a fix)

Apply-side corpus cases **G09–G11** in [`pipeline_golden_v4_corpus.json`](../../apps/api/houston/testing/pipeline_golden_v4_corpus.json) freeze current exact-match behavior:

| Case | Active focus | New candidate focus | Expected today |
| --- | --- | --- | --- |
| G09 | `sirop mojito` | `mojito syrup` | New Signal (no aggregate) |
| G10 | `pain` | `pain blanc` | New Signal (no aggregate) |
| G11 | `clim chambre 104` | `climatisation chambre 104` | New Signal (no aggregate) |

Run:

```bash
make backend-test PYTEST_ARGS='houston/signals/tests/test_pipeline_v4_golden.py -k "G09 or G10 or G11" -q'
```

## Lot 5 evaluation procedure

1. **Deploy pipeline v4** on pilot establishment(s).
2. **Collect 2–4 weeks** of observations + Actions usage (Phase 5 volume).
3. **Weekly report** via management command (per establishment + global).
4. **Prompt iteration (dev-only):** compare live OpenAI output to golden corpus:

   ```bash
   export HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1
   docker compose exec api uv run python manage.py evaluate_observation_pipeline --case-id G01 --case-id G07
   ```

   Structural diff keys: taxonomy routing + normalized `issue_focus` (+ optional `operational_unit_key`). Not run in CI.

5. **Log analysis** (optional): aggregate `active_taxonomy_peer_count > 0` on create events; count `hint_issue_focus_mismatch`.
6. **Manual sample**: review top taxonomy duplicate groups — are focuses genuinely different problems or reformulations?

## Report template (fill during Lot 5)

| Field | Week 1 | Week 2 | Week 3 | Week 4 |
| --- | --- | --- | --- | --- |
| Establishment ID | | | | |
| Active signals | | | | |
| Taxonomy duplicate groups | | | | |
| Signals in duplicate groups | | | | |
| Hint provided (candidates) | | | | |
| Hint issue_focus mismatches | | | | |
| Ops-confirmed false duplicates | | | | |
| Lot 4bis recommended? | | | | |

## Lot 4bis trigger criteria

Lot 4bis is considered **only if** evaluation shows significant impact on **at least one** criterion:

| Criterion | Default indicator (calibrate on pilot) |
| --- | --- |
| Numerous business duplicates not aggregated | `taxonomy_duplicate_group_count >= 3` with ops-confirmed equivalent focuses |
| Frequent reformulations of same problem | `taxonomy_duplicate_signal_count >= 6` across duplicate groups |
| Important `issue_focus` instability | High variance vs golden G07 (aggregate) vs G09–G11 (no aggregate) in live smoke |
| Elevated `hint_issue_focus_mismatch` rate | `hint_issue_focus_mismatch_count / hint_provided_candidate_count >= 0.15` |

**If criteria not met:** keep design A (taxonomy + `issue_focus`); no Lot 4bis.

**If criteria met:** reopen deferred options in order — aliases runtime, expose `issue_focus` read-only, canonical slug, structured entity (last resort). **Do not** introduce fuzzy match or embeddings without explicit guardrails and updated golden corpus.

## Deferred until Lot 4bis decision

- `issue_type` enum
- `issue_entity` / canonical entity model
- Fuzzy matching / embeddings
- Parallel taxonomy
- `RuntimeVocabulary` aliases at apply time

## Related documents

- [`ai_observation_pipeline_contract.md`](../product/domains/ai_observation_pipeline_contract.md)
- [`signal_domain.md`](../product/domains/signal_domain.md)
- [`phase_5_actions_execution_feed.md`](../product/build_plan_mvp/phase_5_actions_execution_feed.md)
