# Chat V1 — Dettes techniques

> **Périmètre** : Chat V1 après Lots 2–7 (socle WS, REST, messages WS, UI Terrain, purge/hardening, doc).  
> **Vérité produit** : [`chat_domain.md`](../product/domains/chat_domain.md).  
> **Contrat API** : [`apps/api/schema.yml`](../../apps/api/schema.yml).  
> **État au 2026-06-09** : **Core implémenté** (Lots 2–6 code + Lot 7 doc) ; dettes produit post-core listées ci-dessous.

---

## 1. Résumé exécutif

| Couche | Maturité | Commentaire |
|--------|----------|-------------|
| Backend REST + modèles | **Élevée** | DM, groupes, unread, seen, permissions, tests REST |
| Backend WebSocket | **Élevée** | Auth ticket, `message.send` / `message.created`, `access_revoked`, broadcast membership-centric, rate limits, tests isolation |
| Purge / inactivation | **Élevée** | Celery Beat, management command, hook membership deactivate, DM delete, auto-promotion admin |
| Observabilité / events | **Faible** | Pas d’`EventEnvelope` chat |
| Frontend Terrain | **Moyenne** | Inbox + fil + WS ; pas de gestion groupe avancée ni settings Owner/Director |
| Documentation produit | **Élevée** | `chat_domain.md`, README, build plan, realtime carve-out alignés (Lot 7) |
| Tests frontend | **Moyenne** | Hook WS Vitest `access.revoked` / reconnect ; pas de E2E Playwright |

**Verdict** : **Core Chat V1 utilisable en dev/staging** (DM, groupes, envoi WS, purge 7j, inactivation, bootstrap `chat_available`). Post-core : events, UI gestion groupe, toggle `chat_enabled`, tests FE WS.

---

## 2. Implémenté (référence rapide)

- **Backend** : `houston/chat/` (models, REST, ws-ticket, consumer, purge, rate limits, ws_notify)
- **Infra** : Daphne, ASGI sans `AuthMiddlewareStack`, proxy Vite `/ws`, Celery purge daily
- **Frontend** : `/chat`, `/chat/:conversationId`, TanStack Query, `useChatWebSocket`, nav masquée si chat indisponible
- **Tests backend** : 54 tests `houston/chat` (REST, ticket, WS auth, messages, idempotence, purge, deactivate, rate limits, hardening)

---

## 3. Dettes techniques ouvertes

### P1 — Important (produit post-core)

| # | Dette | Impact | Détail |
|---|--------|--------|--------|
| 6 | **Events métier absents** | Pas d’audit / analytics internes | Aucun `events.py` ; pas d’émission `EventEnvelope` |
| 7 | **Gestion groupe UI absente** | API REST complète sans surface Terrain | Backend testé ; FE = create DM/groupe + fil seulement |
| 8 | **Toggle `chat_enabled` UI absent** | Owner/Director passent par API ou admin | `PATCH .../chat/settings/` non consommé côté web |

### P2 — Amélioration / écarts plan

| # | Dette | Impact | Détail |
|---|--------|--------|--------|
| 12 | **Groupes conversation WS optionnels non rejoints** | Livraison OK via groupe personnel obligatoire | Complément `chat_est_*_conv_*` non implémenté ; documenté comme non fait |
| 13 | **Recherche conversations côté client uniquement** | Pas de `q` serveur sur `GET conversations/` | Filtre local ; OK petits établissements |
| 14 | **Unread nav = requête REST parallèle** | `App.tsx` charge `conversations` pour point bleu nav | Optimiser via bootstrap ou invalidation WS-only |
| 16 | **Smoke charge WS non automatisé en CI** | Plan Lot 6 : test léger 5 connexions en test backend | Pas de job CI dédié charge |
| 17 | **`handleReconnect` retry failed dans callback WS** | Pattern sensible aux races | Fonctionnel ; couvrir par test ou refactor |
| 18 | **Ruff / format dette repo-wide** | `ruff check .` échoue hors `houston/chat` | Dette transverse |
| 19 | **Chunk JS > 500 kB** | Warning Vite build post Chat UI | Dette perf globale frontend |

### P3 — Confort / post-MVP

| # | Dette | Détail |
|---|--------|--------|
| 20 | Pas de commande management support purge hors participation | Suppression ops journalisée hors API produit |
| 21 | Pas de tests E2E Playwright chat | Validation manuelle seulement |
| 22 | Pas de masquage DM / archivage | Hors scope V1 explicite |
| 23 | Settings chat dans Profil vs espace admin | Emplacement UX à trancher |

---

## 4. Résolu (Lots 6–7 — 2026-06-09)

| # | Dette | Fermeture |
|---|--------|-----------|
| 1 | Purge automatique 7 jours | `purge.py`, Celery Beat, `purge_chat_messages` command |
| 2 | Hook inactivation membership | `handle_membership_chat_deactivation` + hook establishments service |
| 3 | `conversation.access_revoked` | `ws_notify.py`, consumer handler, tests |
| 4 | Documentation produit en retard | Lot 7 : `chat_domain.md`, README, build plan, §12 acceptance |
| 5 | Rate limits WS | REST ws-ticket throttle + `rate_limits.py` message.send |
| 11 | `chat_available` bootstrap absent | `permission_hints.chat_available` dans bootstrap ; FE `bootstrap-permission-hints.ts` — **2026-06-12** |
| 9 | Promotion admin auto | `_ensure_group_has_admin()` on leave/remove/deactivate |
| 10 | Suppression DM à l’inactivation | Service deactivate supprime DM impliquant le membership |
| 15 | Tests FE WS `access.revoked` / reconnect | Vitest `use-chat-websocket.test.ts` couvre global revoke, reconnect réseau, conversation-level — **2026-06-15** |
| 24 | Révocation live WS session / `chat_enabled` / switch établissement | `session_group_name`, `schedule_session_access_revoked`, revalidation `message.send`, tests backend/FE — **2026-06-15** |

Écarts documentation ↔ code (section 4 ancienne version) : **fermés** Lot 7.

---

## 5. Risques restants

| Risque | Sévérité | Mitigation |
|--------|----------|------------|
| Flood messages / tickets résiduel | Faible | Rate limits Lot 6 ; monitorer en pilot |
| Groupe sans admin (edge race) | Faible | Auto-promotion + tests deactivate |
| Doc stale | Faible | Lien permanent vers ce registre ; `chat_domain.md` §12 |
| Régression WS sans tests FE hook | Faible–moyenne | Vitest mock WS (post-core) |
| Events absents pour audit interne | Faible | P1 #6 — décision produit si requis pilot |

---

## 6. Roadmap post-core (hors Lots 2–7)

1. UI gestion groupe (rename, participants, leave, delete)
2. UI toggle `chat_enabled` Owner/Director
3. `EventEnvelope` chat (ids only, no body)
4. Tests FE hook WS + composants composer/retry

---

## 7. Critères de clôture dette (Definition of Done dette)

Une dette P0/P1 est **fermée** seulement si :

- comportement implémenté ou décision produit explicite documentée ;
- test(s) comportementaux ajoutés ou justification écrite ;
- doc produit / OpenAPI alignées ;
- entrée correspondante mise à jour dans ce fichier (date + PR).

---

## 8. Références

- Plan implémentation : `.cursor/plans/chat_v1_realtime_plan_f62dd531.plan.md` (Lots 0–7)
- Acceptance checklist : [`chat_domain.md`](../product/domains/chat_domain.md) §12
- Backend : `apps/api/houston/chat/`
- Frontend : `apps/web/src/features/chat/`
- Auth WS : [`authentication_charter.md`](../architecture/authentication_charter.md) § WebSocket ticket
