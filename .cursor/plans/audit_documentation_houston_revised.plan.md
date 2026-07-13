# Plan révisé — Remise à niveau documentaire Houston (suppression, pas archivage)

**Décision ferme :** Git est l’unique historique. Aucun dossier `archive`, `history`, `legacy` ou équivalent. Actions autorisées : conserver, corriger, réécrire, fusionner puis supprimer, supprimer.

**Comptages vérifiés (glob 2026-07-13) :**

| Ensemble | Nombre exact |
|----------|--------------|
| Fichiers `docs/audits/**` | **54** |
| Fichiers `docs/archive/**` | **26** (24 codex + 2 product/domains) |
| Fichiers `docs/product/domains/**` actuels | **17** → **16** conservés après suppression de `signal_access_grant_domain.md` |
| Fichiers Markdown actifs cibles sous `docs/` | **35** (fourchette annoncée : 35–40) |

**Périmètre volume :** ~35–40 documents actifs sous `docs/` uniquement — **hors** `AGENTS.md`, règles/commandes Cursor, `infra/railway/README.md`, `contracts/**`, `.env*.example`.

---

## Résumé exécutif

La documentation active est noyée sous ~48 000 lignes historiques. Les sources actives les plus dangereuses : [`README.md`](README.md) (notifications/realtime déclarés absents), [`docs/product/mvp_scope.md`](docs/product/mvp_scope.md) (Checklists/Actions legacy), domaines avec liens morts (`feed_domain.md`, `comments_domain.md`, `rbac_permissions_domain.md`).

**Stratégie :** Phase 1 verrouille le manifeste ; Phase 2 crée les canoniques ; Phase 3 corrige les docs conservés (avec liens vers canoniques) ; Phase 4 supprime tout le legacy et répare les références ; Phase 5 installe `scripts/docs_check.py`.

---

## Phase 1 — Vérifications finales et manifeste

### 1.1 Inspections bloquantes

| Source | Action |
|--------|--------|
| [`.env.example`](.env.example), [`.env.prod-test.example`](.env.prod-test.example) | Lire ; valider vs [`docs/deploy/railway_variables.md`](docs/deploy/railway_variables.md) |
| [`Makefile`](Makefile) | 34 cibles ; comparer à toutes les mentions `` `make …` `` dans docs actifs + AGENTS + `.cursor/` |
| [`apps/api/schema.yml`](apps/api/schema.yml) | Référence routes (~80 endpoints `/api/v1/`) |
| Références entrantes | `rg -l '<chemin>'` pour chaque fichier du manifeste marqué **S** ou **F→S** |
| Branding Houston / Spore | Décision : repo/technique = Houston ; UI/PWA = Spore → `current_state.md` |

### 1.2 Hors périmètre suppression

| Chemin | Raison |
|--------|--------|
| [`docs/catalogue/*.csv`](docs/catalogue/) | Données opérationnelles (`make import-catalog`) |
| [`contracts/operational-realtime-invalidation.json`](contracts/operational-realtime-invalidation.json) | Contrat machine |
| [`apps/api/schema.yml`](apps/api/schema.yml) | Contrat HTTP |
| [`.cursor/rules/*.mdc`](.cursor/rules/) | Instructions agent IDE |
| Code, migrations, tests | Hors scan termes legacy (voir Phase 5) |

### 1.3 Décisions produit (défaut si non contesté)

| Sujet | Décision |
|-------|----------|
| `signal_access_grant` | **Supprimer** le doc (aucun modèle dans le code) |
| `.agents/skills/neon-postgres/SKILL.md` | **Supprimer** (tiers, hors Houston) |

### 1.4 Critères de sortie

- Manifeste exhaustif ci-dessous validé
- Références entrantes documentées pour chaque suppression
- `.env*` lus et alignés avec deploy

---

## Phase 2 — Création / réécriture des sources canoniques

| Fichier | Action | Absorbe (vérifié code) |
|---------|--------|------------------------|
| [`docs/product/current_state.md`](docs/product/current_state.md) | **Créer** | Boucle live ; 14 apps ; notifications (`schema.yml`, `notifications/`) ; realtime (`realtime/`, `OperationalRealtimeProvider`) ; chat ; gaps pilot ; branding Spore/Houston ; extraits `lot_11` (alias `can_create_action`, contrat `comment.execution.*`) |
| [`docs/product/mvp_scope.md`](docs/product/mvp_scope.md) | **Réécrire** | Périmètre pilot sans phases historiques ; sans Checklist/Action legacy |
| [`docs/product/decisions/action_plan.md`](docs/product/decisions/action_plan.md) | **Créer** | Décisions §26 + matérialisation schedules |
| [`docs/engineering/local_development.md`](docs/engineering/local_development.md) | **Créer** | Workflow quotidien ; `make` targets ; contenu utile de `fresh_install_validation.md` |
| [`docs/engineering/frontend_architecture.md`](docs/engineering/frontend_architecture.md) | **Créer** | `app-routes.ts` ; Query keys ; PWA `injectManifest`/`sw.ts` |
| [`docs/deploy/smoke_checklist.md`](docs/deploy/smoke_checklist.md) | **Créer** | Fusion smoke QA + Railway |
| [`docs/README.md`](docs/README.md) | **Réécrire** | Index minimal ; ordre de lecture |

### Critères de sortie

- Les 7 fichiers existent et sont référençables
- `decisions/action_plan.md` contient l’intégralité des décisions §26 applicables
- Aucun lien vers chemins qui seront supprimés en Phase 4

---

## Phase 3 — Correction des documents actifs conservés

Exécutée **après** Phase 2 pour pointer vers les canoniques.

| Fichier | Corrections |
|---------|-------------|
| [`README.md`](README.md) | Porte d’entrée : pas d’inventaire exhaustif ; liens `current_state`, `local_development`, deploy ; retirer fausses absences notifications/realtime/Zustand |
| [`INSTALL_MAC.md`](INSTALL_MAC.md) | Install macOS seulement ; lien `local_development.md` pour quotidien ; retirer ref `fresh_install_validation` |
| [`AGENTS.md`](AGENTS.md) | Realtime implémenté (invalidation) |
| [`apps/api/AGENTS.md`](apps/api/AGENTS.md) | Vérifier cohérence ; retirer refs legacy |
| [`apps/web/AGENTS.md`](apps/web/AGENTS.md) | Retirer Zustand actif ou noter non utilisé ; lien `frontend_architecture.md` |
| [`docs/00_ai_documentation_policy.md`](docs/00_ai_documentation_policy.md) | Git = historique ; pas de couche archive |
| [`docs/product/product_principles.md`](docs/product/product_operating_model.md) | Vérifier cohérence MVP ; pas de phases obsolètes |
| 16 × [`docs/product/domains/*.md`](docs/product/domains/) | Voir manifeste domaines |
| [`docs/architecture/authentication_charter.md`](docs/architecture/authentication_charter.md) | Conserver |
| [`docs/architecture/api_error_contract.md`](docs/architecture/api_error_contract.md) | Conserver |
| [`docs/engineering/testing.md`](docs/engineering/testing.md) | Retirer lien `issue_focus_aggregation_eval_lot5.md` |
| [`docs/engineering/api_pagination_standard.md`](docs/engineering/api_pagination_standard.md) | Retirer tickets Checklist ; liens morts |
| [`docs/deploy/prod_test_runbook.md`](docs/deploy/prod_test_runbook.md) | Liens → `smoke_checklist.md` |
| [`docs/deploy/railway_deploy_contract.md`](docs/deploy/railway_deploy_contract.md) | Absorber note PR3 static ; retirer refs `prod_test_decisions`, `railway_static_frontend` |
| [`docs/deploy/railway_architecture.md`](docs/deploy/railway_architecture.md) | Absorber `prod_test_decisions` ; corriger PWA |
| [`docs/deploy/railway_variables.md`](docs/deploy/railway_variables.md) | Conserver |
| [`docs/deploy/railway_security.md`](docs/deploy/railway_security.md) | Retirer ref `prod_test_decisions` |
| [`infra/railway/README.md`](infra/railway/README.md) | Aligner liens deploy |
| [`.cursor/rules/000-project-contract.mdc`](.cursor/rules/000-project-contract.mdc), [`30-docker-orbstack.mdc`](.cursor/rules/30-docker-orbstack.mdc) | Aligner realtime |
| [`.cursor/commands/audit-mode.md`](.cursor/commands/audit-mode.md) | Ne plus cibler `docs/audits/` |

### Critères de sortie

- Aucune affirmation connue fausse dans les fichiers conservés
- README = porte d’entrée (pas catalogue complet implémenté/non implémenté)
- Domain docs : headers `Status:` et `Implementation status:` présents

---

## Phase 4 — Suppression massive et réparation des références

**Ordre :** extraire contenu utile (Phase 2) → supprimer fichiers → `rg` références → corriger tous les liens dans le même lot.

**Dossiers à supprimer entièrement :** `docs/archive/`, `docs/audits/`, `docs/evolution_action/`, `docs/product/build_plan_mvp/`, `docs/qa/`, `docs/design/`, `.agents/skills/neon-postgres/` (si présent).

### Critères de sortie

- Aucun des dossiers ci-dessus n’existe
- `rg` chemins supprimés dans docs actifs + README + INSTALL + AGENTS + `.cursor/` → **0**
- Aucun lien Markdown cassé

---

## Phase 5 — Contrôle anti-dérive

### Script unique : [`scripts/docs_check.py`](scripts/docs_check.py)

**Périmètre de scan :** documentation active et instructions agent uniquement :

- `README.md`, `INSTALL_MAC.md`, `AGENTS.md`, `apps/*/AGENTS.md`
- `docs/**/*.md` (état post-migration)
- `.cursor/rules/**/*.mdc`, `.cursor/commands/**/*.md`
- `infra/railway/README.md`

**Exclu du scan termes legacy :** `apps/api/**`, migrations, tests, `docs/catalogue/`, `contracts/`, code source.

**Vérifications :**

| # | Contrôle |
|---|----------|
| 1 | Liens Markdown relatifs `](path)` → cible existe |
| 2 | Fichiers référencés inexistants |
| 3 | Commandes `` `make <target>` `` citées → cible dans `Makefile` |
| 4 | Chemins documentaires interdits : `docs/archive/`, `docs/audits/`, `docs/evolution_action/`, `docs/product/build_plan_mvp/`, `docs/qa/`, `docs/design/` |
| 5 | Termes Action/Checklist **legacy présentés comme actifs** (heuristiques : `houston/actions`, `houston/checklists`, `execution-feed/`, « Checklist domain », « Action domain » hors contexte historique explicite) |
| 6 | Chaque `docs/product/domains/*.md` : headers `Status:` et `Implementation status:` |
| 7 | Absence physique des dossiers supprimés (Phase 4) |
| 8 | README : heuristique porte d’entrée — doit référencer `current_state.md` et `local_development.md` ; ne doit pas contenir de section « What Is Not Implemented Yet » exhaustive (pattern configurable) |

**Non inclus :** limite de lignes README ; obligation de modifier `Last reviewed` ; scan migrations/code.

### CI

```yaml
docs-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - run: python scripts/docs_check.py
```

Pas de `make verify` pour changements Markdown seuls.

---

## Arborescence cible (`docs/` = 35 fichiers)

```text
docs/                                          # 35 fichiers .md
  README.md
  00_ai_documentation_policy.md
  product/
    current_state.md                           # Cr
    mvp_scope.md                               # R
    product_principles.md                      # C
    product_operating_model.md                 # C
    domains/                                   # 16 fichiers (C/Co/R)
    decisions/
      action_plan.md                           # Cr
  architecture/
    authentication_charter.md                  # C
    api_error_contract.md                      # C
  engineering/
    local_development.md                       # Cr
    frontend_architecture.md                   # Cr
    testing.md                                 # C
    api_pagination_standard.md                 # Co
  deploy/
    prod_test_runbook.md                       # Co
    railway_deploy_contract.md                 # Co
    railway_architecture.md                    # Co
    railway_variables.md                       # C
    railway_security.md                        # Co
    smoke_checklist.md                         # Cr
```

Hors `docs/` conservés : racine README/INSTALL/AGENTS, `apps/*/AGENTS.md`, `.cursor/`, `infra/railway/README.md`, `contracts/`, `.env*.example`, `docs/catalogue/*.csv`.

---

## Manifeste exhaustif

Colonnes : **Action** = C conserver · Co corriger · R réécrire · Cr créer · F→S fusionner puis supprimer · S supprimer

### Racine et agents (hors `docs/` — hors quota 35–40)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `README.md` | R | — | — | `INSTALL_MAC.md`, `infra/railway/README.md` | Fausses infos notifications/realtime ; trop long |
| `INSTALL_MAC.md` | Co | workflow → `local_development` | `docs/engineering/local_development.md` | `README.md` | Install macOS ; L23 → `fresh_install_validation` |
| `AGENTS.md` | Co | — | — | `.cursor/rules/000-project-contract.mdc` | Realtime « deferred » faux |
| `apps/api/AGENTS.md` | C | — | — | racine `AGENTS.md` | Aligné code |
| `apps/web/AGENTS.md` | Co | détails FE → `frontend_architecture` | `docs/engineering/frontend_architecture.md` | racine `AGENTS.md` | Zustand documenté, 0 import `src/` |
| `.env.example` | C | — | — | `README.md`, `INSTALL_MAC.md`, deploy | Contrat env local |
| `.env.prod-test.example` | C | — | — | `README.md`, deploy | Contrat prod-test |

### `.cursor/rules/` (8 fichiers)

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `.cursor/rules/000-project-contract.mdc` | Co | — | — | alwaysApply | Aligner realtime |
| `.cursor/rules/01-agent-guardrails.mdc` | C | — | — | — | Unique |
| `.cursor/rules/10-backend-django-drf.mdc` | C | — | — | — | Subset api AGENTS |
| `.cursor/rules/20-frontend-react-vite-ts.mdc` | C | — | — | — | Subset web AGENTS |
| `.cursor/rules/21-mobile-first-pwa.mdc` | C | — | — | — | PWA |
| `.cursor/rules/30-docker-orbstack.mdc` | Co | — | — | — | Refs docs |
| `.cursor/rules/80-security-data-integrity.mdc` | C | — | — | — | Sécurité |
| `.cursor/rules/90-rule-authoring.mdc` | C | — | — | — | Meta |

### `.cursor/commands/` (16 fichiers)

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `.cursor/commands/implementation-mode.md` | C | — | — | — | Workflow |
| `.cursor/commands/audit-mode.md` | Co | — | — | — | Cible `docs/audits/` supprimée |
| `.cursor/commands/ticket-scope.md` | C | — | — | — | Template |
| `.cursor/commands/need-scope.md` | C | — | — | — | Template |
| `.cursor/commands/review-diff.md` | C | — | — | — | Review |
| `.cursor/commands/review-before-commit.md` | C | — | — | — | Review court |
| `.cursor/commands/api-contract-change.md` | C | — | — | `testing.md` | OpenAPI |
| `.cursor/commands/backend-fix.md` | C | — | — | `testing.md` | Backend |
| `.cursor/commands/frontend-fix.md` | C | — | — | — | Frontend |
| `.cursor/commands/domain-lifecycle-change.md` | C | — | — | — | Lifecycle |
| `.cursor/commands/rbac-scope-change.md` | C | — | — | — | RBAC |
| `.cursor/commands/event-driven.md` | C | — | — | — | Events |
| `.cursor/commands/realtime-ws-change.md` | C | — | — | — | WS |
| `.cursor/commands/mobile-pwa-ui-change.md` | C | — | — | — | PWA UI |
| `.cursor/commands/test-audit.md` | C | — | — | — | Tests ; pas de ref audits |

### `infra/`

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `infra/railway/README.md` | Co | — | — | `README.md` | Liens deploy post-fusion |

### `.agents/`

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `.agents/skills/neon-postgres/SKILL.md` | S | — | — | audits (supprimés) | Tiers ; hors Houston |

---

### `docs/` — fichiers conservés ou créés (35)

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `docs/README.md` | R | — | — | — | Arbre obsolète Build_Plan, evolution_action |
| `docs/00_ai_documentation_policy.md` | Co | — | — | tous agents | Retirer archive comme source |
| `docs/product/current_state.md` | **Cr** | lot_11, README vérité produit | — | `README.md` (nouveau) | Snapshot implémenté |
| `docs/product/mvp_scope.md` | R | — | — | `README.md` | Phases Checklist/Action legacy |
| `docs/product/product_principles.md` | C | — | — | — | authoritative |
| `docs/product/product_operating_model.md` | C | — | — | — | authoritative |
| `docs/product/decisions/action_plan.md` | **Cr** | §26 + materialization | — | domaines feed, rbac | Décisions applicables |
| `docs/engineering/local_development.md` | **Cr** | fresh_install | — | `README.md`, `INSTALL_MAC.md` | Workflow quotidien |
| `docs/engineering/frontend_architecture.md` | **Cr** | — | — | `apps/web/AGENTS.md` | Carte FE |
| `docs/deploy/smoke_checklist.md` | **Cr** | 3 QA + railway smoke | — | runbook | Smoke unique |
| `docs/architecture/authentication_charter.md` | C | — | — | `INSTALL_MAC.md` | OK |
| `docs/architecture/api_error_contract.md` | C | — | — | `INSTALL_MAC.md` | OK |
| `docs/engineering/testing.md` | Co | — | — | cursor commands | Retirer lien issue_focus |
| `docs/engineering/api_pagination_standard.md` | Co | — | — | — | Tickets Checklist obsolètes |
| `docs/deploy/prod_test_runbook.md` | Co | — | — | `README.md` | Liens smoke, decisions |
| `docs/deploy/railway_deploy_contract.md` | Co | static PR3 | — | infra, README | Fusion static_frontend |
| `docs/deploy/railway_architecture.md` | Co | prod_test_decisions | — | `README.md`, infra | PWA stale ; fusion décisions |
| `docs/deploy/railway_variables.md` | C | — | — | `README.md`, infra | Matrice env |
| `docs/deploy/railway_security.md` | Co | — | — | — | Retirer prod_test_decisions |

### `docs/product/domains/` (17 actuels → 16 conservés)

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `docs/product/domains/identity_membership_domain.md` | C | — | — | `INSTALL_MAC.md` | OK |
| `docs/product/domains/rbac_permissions_domain.md` | Co | materialization → decisions | `decisions/action_plan.md` | — | L185 liens archive, evolution_action |
| `docs/product/domains/business_unit_taxonomy_domain.md` | Co | note v1→v2 | (interne) | `ai_observation_pipeline_contract.md` | Lien taxonomy_v1 |
| `docs/product/domains/runtime_config_onboarding_domain.md` | C | — | — | `README.md`, `INSTALL_MAC` | OK |
| `docs/product/domains/observation_domain.md` | C | — | — | — | Aligné schema |
| `docs/product/domains/ai_domain.md` | C | — | — | — | OK |
| `docs/product/domains/ai_observation_pipeline_contract.md` | Co | — | — | `INSTALL_MAC.md` | Lien taxonomy_v1 L121 |
| `docs/product/domains/signal_domain.md` | C | — | — | — | OK post-Lot 11 |
| `docs/product/domains/feed_domain.md` | Co | besoin §25, materialization | `decisions/action_plan.md` | — | L5 archive ; L40,151,185,216 evolution_action |
| `docs/product/domains/feed_subscription_domain.md` | C | — | — | — | Deferred explicite |
| `docs/product/domains/signal_access_grant_domain.md` | **S** | — | — | — | candidate ; aucun modèle code |
| `docs/product/domains/notification_domain.md` | Co | Lot2 backlog bref | (interne) | — | L41,161 → notification_matrix |
| `docs/product/domains/realtime_domain.md` | C | — | — | `comments_domain` | OK ; JSON contract |
| `docs/product/domains/chat_domain.md` | Co | — | — | `README.md` | Frontière notifications |
| `docs/product/domains/comments_domain.md` | R | — | — | — | Draft ; §2 faux ; L300 event_catalogue |
| `docs/product/domains/upload_media_domain.md` | C | — | — | — | OK |
| `docs/product/domains/security_rgpd_domain.md` | C | — | — | — | OK |

---

### `docs/product/` — suppressions (8 fichiers)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/product/event_catalogue_v0.1.md` | S | rien (JSON + constants) | `notifications/constants.py`, `contracts/operational-realtime-invalidation.json` | `comments_domain.md`, `notification_matrix`, audits | ARCHIVED ; domaines action/checklist supprimés |
| `docs/product/notification_matrix_v0.2.md` | F→S | Lot2 backlog bref | `notification_domain.md` | `notification_domain.md`, audits | Duplique `LOT1_EVENT_KEYS` |
| `docs/product/phase_a_closure.md` | S | — | `business_unit_taxonomy_domain.md` | `taxonomy_v1_to_v2_migration.md` | historical closed A8 |
| `docs/product/taxonomy_v1_to_v2_migration.md` | F→S | paragraphe migration | `business_unit_taxonomy_domain.md` | `business_unit_taxonomy`, `phase_a_closure`, `ai_observation_pipeline` | Migration Lot 6 terminée |

### `docs/product/build_plan_mvp/` (3 fichiers — tous **S**)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/product/build_plan_mvp/houston_mvp_build_plan.md` | S | état produit | `current_state.md`, `mvp_scope.md` | `docs/README.md`, `ticket_8_validation_report` | Build Plan terminé ; Checklists ✅ faux |
| `docs/product/build_plan_mvp/phase_4_ai_pipeline_signal_feed.md` | S | — | domaines `ai_*`, `signal` | audits, `issue_focus` | Phase livrée |
| `docs/product/build_plan_mvp/phase_5_actions_execution_feed.md` | S | — | — | `issue_focus`, `action_audit` | 100 % legacy Action |

### `docs/evolution_action/` (3 fichiers)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/evolution_action/besoin_evolution_action.md` | S | — | `decisions/action_plan.md` (déjà extrait) | `docs/README.md`, `feed_domain`, audits | Expression de besoin ; décisions signées |
| `docs/evolution_action/decisions_plan_action.md` | F→S | §26 entier | `product/decisions/action_plan.md` | `docs/README.md`, audits | Renommage chemin cible |
| `docs/evolution_action/action_plan_materialization.md` | F→S | règles schedules | `product/decisions/action_plan.md` | `feed_domain`, `rbac`, `phase_2_final_roadmap` | Décision Lot 4 live dans code |

### `docs/engineering/` — suppression (1 fichier)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/engineering/issue_focus_aggregation_eval_lot5.md` | S | — | — | `testing.md` L162 | Eval Lot 5 ponctuel |

### `docs/qa/` (4 fichiers)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/qa/fresh_install_validation.md` | F→S | séquences E2E | `engineering/local_development.md` | `README.md` L130, `INSTALL_MAC.md` L23, audits | Validation ponctuelle |
| `docs/qa/pilot_smoke_checklist.md` | F→S | parcours pilot | `deploy/smoke_checklist.md` | `fresh_install_validation`, `prod_test_smoke` | Duplication smoke |
| `docs/qa/prod_test_smoke.md` | F→S | parcours prod-test | `deploy/smoke_checklist.md` | `prod_test_runbook`, `railway_smoke` | Duplication smoke |
| `docs/qa/ticket_8_validation_report.md` | S | — | — | audits PWA | Rapport ponctuel 2026-06-03 |

### `docs/deploy/` — suppressions (3 fichiers)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/deploy/prod_test_decisions.md` | F→S | décisions figées V1 | `railway_architecture.md` + `railway_deploy_contract.md` | `README.md` L112, runbook, security, architecture, contract | Duplication deploy |
| `docs/deploy/railway_smoke_checklist.md` | F→S | checks techniques | `deploy/smoke_checklist.md` | `prod_test_runbook`, `prod_test_smoke`, contract | Fusion smoke |
| `docs/deploy/railway_static_frontend.md` | F→S | note PR3 same-origin | `railway_deploy_contract.md` | `railway_architecture`, `railway_smoke` | PR3 historique |

### `docs/design/` (1 fichier)

| Fichier actuel | Action | Contenu absorbé | Canonique | Références entrantes | Justification |
|----------------|--------|-----------------|-----------|----------------------|---------------|
| `docs/design/prototype/houston_mockup.html` | S | — | — | aucune | Prototype historique |

---

### `docs/archive/codex/` (24 fichiers — tous **S**)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/archive/codex/phase_0_1_foundations.md` | S | — | domaines actifs condensés | audits uniquement | Phase 0 historique |
| `docs/archive/codex/phase_0_2_foundation_hardening.md` | S | — | — | audits | Idem |
| `docs/archive/codex/phase_0_3_core_primitives.md` | S | — | — | audits | Idem |
| `docs/archive/codex/phase_0_4_identity_access_foundation.md` | S | — | `identity_membership_domain.md` | audits | Remplacé |
| `docs/archive/codex/phase_0_5_web_auth_foundation.md` | S | — | `authentication_charter.md` | audits | Remplacé |
| `docs/archive/codex/phase_0_6_minimal_rbac_permission_service.md` | S | — | `rbac_permissions_domain.md` | audits | Remplacé |
| `docs/archive/codex/phase_0_7_phase_0_closure_gate.md` | S | — | — | audits | Idem |
| `docs/archive/codex/houston_product_overview.md` | S | — | `mvp_scope`, `product_operating_model` | audits | ~6000 lignes obsolètes |
| `docs/archive/codex/houston_technical_architecture_erd_final.md` | S | — | code + `schema.yml` | audits, codex cross-refs | ERD historique ; chemins actions/checklists |
| `docs/archive/codex/houston_action_domain.md` | S | — | `decisions/action_plan.md`, domaines action_plans | audits | Domaine supprimé Lot 10 |
| `docs/archive/codex/houston_checklist_domain.md` | S | — | — | audits | Domaine supprimé Lot 10 |
| `docs/archive/codex/houston_observation_domain.md` | S | — | `observation_domain.md` | audits | Remplacé |
| `docs/archive/codex/houston_signal_domain.md` | S | — | `signal_domain.md` | audits | Remplacé |
| `docs/archive/codex/houston_ai_observation_pipeline_contract.md` | S | — | `ai_observation_pipeline_contract.md` | audits | Remplacé |
| `docs/archive/codex/houston_ai_overview.md` | S | — | `ai_domain.md` | audits | Remplacé |
| `docs/archive/codex/houston_ai_onboarding_contract.md` | S | — | — | audits | AI onboarding retiré |
| `docs/archive/codex/houston_ai_transcription_contract.md` | S | — | `observation_domain.md` | audits | Partiellement couvert |
| `docs/archive/codex/houston_onboarding_domain.md` | S | — | `runtime_config_onboarding_domain.md` | `onboarding_audit` | Remplacé |
| `docs/archive/codex/houston_authentication_identity_domain.md` | S | — | `identity_membership_domain.md` | audits, codex | Remplacé |
| `docs/archive/codex/houston_rbac_permissions_domain.md` | S | — | `rbac_permissions_domain.md` | audits | Remplacé |
| `docs/archive/codex/houston_notification_matrix.md` | S | — | `notification_domain.md` | codex cross-refs | Remplacé |
| `docs/archive/codex/houston_feed_query_sorting_contract.md` | S | — | `feed_domain.md` | codex | Remplacé |
| `docs/archive/codex/houston_upload_media_lifecycle.md` | S | — | `upload_media_domain.md` | codex | Remplacé |
| `docs/archive/codex/houston_security_rgpd_baseline.md` | S | — | `security_rgpd_domain.md` | codex | Remplacé |

### `docs/archive/product/domains/` (2 fichiers — tous **S**)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/archive/product/domains/action_domain.md` | S | — | `decisions/action_plan.md` | `feed_domain.md`, `rbac_permissions_domain.md`, `notification_matrix` | Domaine archivé post-Lot 10 |
| `docs/archive/product/domains/checklist_domain.md` | S | — | — | `notification_matrix`, audits | Domaine supprimé |

---

### `docs/audits/` (54 fichiers — tous **S**)

| Fichier actuel | Action | Contenu absorbé | Canonique cible | Références entrantes | Justification |
|----------------|--------|-----------------|-----------------|----------------------|---------------|
| `docs/audits/README.md` | S | — | — | — (auto) | Index audits ; plus d’audits actifs |
| `docs/audits/action_audit.md` | S | — | — | consolidations, audits | Legacy Action ; audit clos |
| `docs/audits/action_consolidation.md` | S | — | — | audits croisés | Idem |
| `docs/audits/action_plan_execution_feed_sort_audit.md` | S | — | — | — | UX audit ponctuel juillet 2026 |
| `docs/audits/action_plan_execution_task_layout_audit.md` | S | — | — | `action_plan_task_detail_harmonization` | UX audit |
| `docs/audits/action_plan_task_assignee_pole_audit.md` | S | — | — | — | UX audit |
| `docs/audits/action_plan_task_detail_harmonization_audit.md` | S | — | — | — | UX audit |
| `docs/audits/action_plan_task_enrichment_audit.md` | S | — | — | — | UX audit |
| `docs/audits/action_plan_task_layout_final_audit.md` | S | — | — | — | UX audit |
| `docs/audits/action_plan_task_pole_ux_audit.md` | S | — | — | — | UX audit |
| `docs/audits/action_plan_task_uncheck_audit.md` | S | — | — | — | UX audit |
| `docs/audits/action_plans_event_planning_audit.md` | S | — | — | — | UX audit |
| `docs/audits/ai_pipeline_audit.md` | S | — | — | audits | Audit clos juin 2026 |
| `docs/audits/backend_core_architecture.md` | S | — | — | audits | Audit architecture |
| `docs/audits/checklist_audit.md` | S | — | — | audits | Domaine Checklist supprimé |
| `docs/audits/checklist_consolidation.md` | S | — | — | audits | Idem |
| `docs/audits/execution_feed_audit.md` | S | — | — | audits | Legacy execution feed |
| `docs/audits/execution_feed_consolidation.md` | S | — | — | audits | Idem |
| `docs/audits/feature_audit_closure.md` | S | — | — | `phase_2_final_roadmap` | Registre closure ; absorbé en code |
| `docs/audits/feature_audit_decisions.md` | S | — | — | closure | Decision pack doc-only |
| `docs/audits/global_architecture_mapping.md` | S | — | — | audits | Cartographie juin 2026 |
| `docs/audits/lot_11_stabilization_audit.md` | S | conclusions F11 | `current_state.md`, domaines corrigés Phase 3 | `audits/README.md` | Audit clos ; pas d’exception récence |
| `docs/audits/notifications_realtime_audit.md` | S | — | domaines notification/realtime | audits | Audit clos |
| `docs/audits/notifications_realtime_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/observation_audit.md` | S | — | `observation_domain.md` | audits | Audit clos |
| `docs/audits/observation_refresh_audit.md` | S | — | — | audits | Audit clos |
| `docs/audits/observation_refresh_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/onboarding_audit.md` | S | — | `runtime_config_onboarding_domain.md` | audits | Audit clos |
| `docs/audits/onboarding_observation_ai_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_api_openapi_audit.md` | S | — | `schema.yml` | audits | Phase 2 clos |
| `docs/audits/phase_2_api_openapi_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_audit_backlog.md` | S | — | — | audits | Backlog infra |
| `docs/audits/phase_2_celery_async_audit.md` | S | — | code Celery | audits | Phase 2 clos |
| `docs/audits/phase_2_celery_async_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_ci_devex_docs_audit.md` | S | — | `local_development.md` | audits | DevEx ; findings intégrés plan |
| `docs/audits/phase_2_ci_devex_docs_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_database_orm_audit.md` | S | — | — | audits | Phase 2 clos |
| `docs/audits/phase_2_database_orm_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_final_roadmap.md` | S | — | — | audits | Roadmap vivante obsolète |
| `docs/audits/phase_2_frontend_architecture_audit.md` | S | — | `frontend_architecture.md` | audits | Phase 2 clos |
| `docs/audits/phase_2_frontend_architecture_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_pwa_mobile_first_audit.md` | S | — | `frontend_architecture.md` | audits | Phase 2 clos |
| `docs/audits/phase_2_pwa_mobile_first_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_realtime_event_driven_audit.md` | S | — | `realtime_domain.md` | audits | Phase 2 clos |
| `docs/audits/phase_2_realtime_event_driven_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_tanstack_query_cache_audit.md` | S | — | `frontend_architecture.md` | audits | Phase 2 clos |
| `docs/audits/phase_2_tanstack_query_cache_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/phase_2_test_strategy_audit.md` | S | — | `testing.md` | audits | Phase 2 clos |
| `docs/audits/phase_2_test_strategy_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/rbac_security_audit.md` | S | — | `rbac_permissions_domain.md` | audits | Audit clos |
| `docs/audits/signal_feed_audit.md` | S | — | `signal_domain.md`, `feed_domain.md` | audits | Audit clos |
| `docs/audits/signal_feed_consolidation.md` | S | — | — | audits | Consolidation |
| `docs/audits/test_suite_audit.md` | S | — | `testing.md` | audits | Audit tests |
| `docs/audits/ts_e1_existing_dates_batch_audit.md` | S | — | — | audits | Batch audit ponctuel |

---

### Fichier créé (hors liste suppression)

| Fichier | Action |
|---------|--------|
| `scripts/docs_check.py` | **Cr** (Phase 5) |

---

## Synthèse suppressions

| Dossier / groupe | Fichiers |
|------------------|----------|
| `docs/archive/codex/` | 24 |
| `docs/archive/product/domains/` | 2 |
| `docs/audits/` | 54 |
| `docs/product/build_plan_mvp/` | 3 |
| `docs/evolution_action/` | 3 |
| `docs/qa/` | 4 |
| `docs/product/` (racine obsolètes) | 4 |
| `docs/product/domains/signal_access_grant_domain.md` | 1 |
| `docs/engineering/issue_focus_aggregation_eval_lot5.md` | 1 |
| `docs/deploy/` (redondants) | 3 |
| `docs/design/prototype/houston_mockup.html` | 1 |
| `.agents/skills/neon-postgres/SKILL.md` | 1 |
| **Total suppressions** | **101** |

---

## Critères d’acceptation finaux

- [ ] Aucun dossier `docs/archive/`, `docs/audits/`, `docs/evolution_action/`, `docs/product/build_plan_mvp/`, `docs/qa/`, `docs/design/`
- [ ] Aucun audit, Build Plan, spec Codex, doc Action/Checklist legacy dans le dépôt
- [ ] ~35 fichiers `.md` actifs sous `docs/` (35–40)
- [ ] Aucune référence à un fichier supprimé dans docs actifs + README + INSTALL + AGENTS + `.cursor/` + `infra/railway/README.md`
- [ ] Aucune affirmation connue fausse
- [ ] README = porte d’entrée sans inventaire exhaustif ; pointe vers `current_state.md` et `local_development.md`
- [ ] Pas de duplication majeure entre README, `current_state`, `mvp_scope`, domaines
- [ ] `python scripts/docs_check.py` vert ; job CI `docs-check` vert
- [ ] Historique = Git uniquement

---

## 10 actions prioritaires

1. Phase 1 : lire `.env*` ; valider manifeste 54+26+101 suppressions
2. Phase 2 : créer `current_state.md` (absorbe lot_11)
3. Phase 2 : créer `decisions/action_plan.md`, `local_development.md`, `frontend_architecture.md`, `smoke_checklist.md`
4. Phase 2 : réécrire `mvp_scope.md`, `docs/README.md`
5. Phase 3 : corriger README, AGENTS, 16 domaines, deploy
6. Phase 4 : supprimer `docs/archive/**` (26)
7. Phase 4 : supprimer `docs/audits/**` (54)
8. Phase 4 : supprimer build_plan, evolution_action, qa, product obsolètes, deploy redondants, design, neon skill
9. Phase 4 : réparer toutes références entrantes
10. Phase 5 : `scripts/docs_check.py` + CI

---

## Risques / non vérifié

- Contenu exact `.env.example` / `.env.prod-test.example` (lecture sandbox refusée)
- Exhaustivité références entrantes pour les 101 suppressions (script `rg` obligatoire en Phase 1)
- Gaps UI chat — confirmation manuelle pour `current_state.md`
- Matrice complète producteurs notification vs `LOT1_EVENT_KEYS`

---

**Changed :** plan enregistré mis à jour (`.cursor/plans/audit_documentation_houston_revised.plan.md`)  
**Validated :** comptages 54 audits, 26 archive, 17→16 domaines, 35 docs cibles  
**Risks / not verified :** `.env*` ; exécution non démarrée (attente validation)
