# EventEnvelope & houston.events — inventaire confirmé (Lot 1)

## Runtime

| Élément | Chemin | Usage prod confirmé |
|---------|--------|---------------------|
| `EventEnvelope` dataclass | `apps/api/houston/core/events.py` | **Aucun import applicatif** hors tests (grep `from houston.core.events` → tests only) |
| App Django `houston.events` | `apps/api/houston/events/` | Config vide (`apps.py`), **aucun modèle**, migrations vides |
| `INSTALLED_APPS` | `apps/api/config/settings.py` L53 | `"houston.events"` enregistré |
| Side effects runtime réels | `houston/realtime/broadcast.py`, `houston/notifications/scheduling.py` | Post-commit hubs (documentés AGENTS.md) — **pas** EventEnvelope |

## Tests

| Fichier | Tests | Nature |
|---------|-------|--------|
| `apps/api/houston/core/tests/test_events.py` | 3 | Defaults dataclass (id, timestamp, optional fields, payload isolation) |

## Documentation / dette

| Référence | Mention |
|-----------|---------|
| `apps/api/AGENTS.md` | Scaffolding non-runtime, tests only |
| `docs/product/domains/ai_domain.md` | Category set includes `ai` — pas de catalog AI events |
| `docs/product/domains/chat_domain.md` | EventEnvelope payloads sans message body (planifié) |
| `docs/product/domains/security_rgpd_domain.md` | Categories technical/ai/audit — pas de catalog sécurité |

## Décision Lot 2 (hors scope Lot 1)

Option A : conserver scaffolding + tests  
Option B : suppression complète (code, app, INSTALLED_APPS, tests, docs)

**Gain CI mesuré attendu** : négligeable (3 tests) — à confirmer après baseline pytest.
