# Lot 7 — Proposition Playwright (non implémentée)

Ce document décrit l’infrastructure E2E minimale pour couvrir 3 parcours critiques. **Aucun fichier Playwright n’a été ajouté** : la stack actuelle ne contient ni `@playwright/test`, ni config, ni job CI dédié. Implémenter ces scénarios nécessite un lot infra distinct (hors scope PR CI existante).

## État actuel

| Élément | Statut |
|---------|--------|
| `@playwright/test` dans `apps/web/package.json` | Absent |
| `playwright.config.ts` | Absent |
| Specs E2E | Absent |
| Job CI Playwright | Absent (volontaire — ne pas toucher la CI PR) |
| Couverture équivalente | Backend journey pytest + Vitest purge cache auth |

## Prérequis infra (estimation ~1–2 jours)

### 1. Dépendances et config

```bash
cd apps/web && npm install -D @playwright/test
npx playwright install chromium
```

Fichier `apps/web/playwright.config.ts` :

- `testDir`: `e2e/`
- `baseURL`: `http://127.0.0.1:5173`
- `webServer`: `[{ command: 'npm run dev', port: 5173, reuseExistingServer: !process.env.CI }, { command: 'docker compose up api -d', ... }]` ou une cible Makefile proposée `e2e-stack` (à implémenter avec l’infra Playwright — **non disponible aujourd’hui**)
- `timeout`: 60_000 (pipeline fake AI + bootstrap)
- `retries`: 1 en CI nightly uniquement

### 2. Seed déterministe

Script Django management ou fixture pytest réutilisable :

- Utilisateur `e2e_owner@houston.local` / mot de passe fixe (`TEST_PASSWORD` backend)
- 2 établissements (`E2E Hotel A`, `E2E Hotel B`) avec taxonomie hotel/maintenance
- Membership OWNER sur les deux
- Commande : `docker compose exec api uv run python manage.py seed_e2e_fixtures --reset`

Réutiliser `houston/testing/factories.py`, `create_restaurant_v3_taxonomy` / `setup_hotel_taxonomy`, `build_api_membership`.

### 3. Sélecteurs stables (à ajouter au code produit)

| Action | Sélecteur proposé | Fichier cible |
|--------|-------------------|---------------|
| Login email | `data-testid="login-email"` | `login-form.tsx` |
| Login password | `data-testid="login-password"` | `login-form.tsx` |
| Login submit | `data-testid="login-submit"` | `login-form.tsx` |
| Sign out | `data-testid="sign-out"` | `App.tsx` |
| Nav terrain | `data-testid="nav-terrain"` | shell nav |
| Submit observation | `data-testid="observation-submit"` | terrain form |
| Signal feed item | `data-testid="signal-feed-item"` | signal card |
| Switch establishment | `data-testid="switch-establishment-{id}"` | profile-switch page |

Éviter les sélecteurs texte FR (`Actif`, `Brasserie Metz`) — fragiles i18n.

### 4. Helpers E2E

`apps/web/e2e/helpers/auth.ts` :

- `login(page, { email, password })` — CSRF cookie + POST login + attente bootstrap
- `switchEstablishment(page, establishmentId)` — clic bouton testid
- `waitForSignalFeed(page, { minItems: 1 })`

`apps/web/e2e/helpers/api.ts` (optionnel) :

- `runObservationPipeline(observationId)` via `docker compose exec api` pour accélérer le scénario 3 si Celery worker non démarré en E2E

## 3 scénarios proposés

### Scénario 1 — Login → bootstrap → terrain

**Objectif** : parcours d’accès opérationnel minimal.

**Steps** :

1. Aller sur `/login`
2. Saisir credentials seed
3. Attendre redirect bootstrap (establishment actif ou sélection si multi)
4. Naviguer vers `/terrain` via `data-testid="nav-terrain"`
5. Assert : page terrain visible, pas d’erreur 401, bootstrap `active_membership` affiché

**Doublons évités** : couvert partiellement par Vitest `App.login.test.tsx` (mocked auth) — E2E valide le vrai stack HTTP + cookies.

### Scénario 2 — Changement d’établissement sans fuite tenant

**Objectif** : isolation cache/UI entre établissements.

**Steps** :

1. Login utilisateur multi-établissement (seed)
2. Injecter ou charger un signal connu dans feed A (via API seed ou UI si signal pré-créé)
3. Noter titre signal visible sur `/signals` (establishment A)
4. Switch vers establishment B via profile switch
5. Assert : feed B ne contient **pas** le signal de A
6. Switch retour A → signal A réapparaît (refetch)

**Doublons évités** :

- Backend : `test_submit_observation_signal_not_visible_in_other_establishment_feed`
- Frontend : `api.test.ts` purge cache, `profile-switch-establishment-cache.test.tsx` purge UI→API

E2E valide l’absence de fuite **visible** dans le DOM après switch.

### Scénario 3 — Observation → signal (provider fake)

**Objectif** : parcours produit complet terrain.

**Steps** :

1. Login + navigation terrain (établissement avec taxonomie seed)
2. Soumettre texte observation (≥ 20 chars, texte fixe seed)
3. Attendre statut processing `signal_created` (polling UI ou `data-testid="processing-status"`)
4. Naviguer feed signals
5. Assert : 1 item feed avec titre fake provider (`Structured issue` ou payload seed custom)

**Prérequis** :

- `HOUSTON_AI_OBSERVATION_PROVIDER=fake` (déjà default dev)
- Celery worker actif **ou** hook test `process_observation_task.run` post-submit via API interne

**Doublons évités** :

- Backend : `test_observation_signal_feed_journey.py` (HTTP submit → task.run → feed)
- Pas de test OpenAI live

## Exécution locale proposée

```bash
make e2e-seed          # seed fixtures
make e2e               # playwright test (apps/web)
make e2e-ui              # playwright test --ui
```

Makefile cible (à créer) — **hors CI PR** ; option nightly workflow séparé.

## Risques et garde-fous

- **Flakiness Celery** : préférer worker dédié E2E ou appel synchrone `process_observation_task.run` dans seed hook post-submit
- **CSRF / cookies** : Playwright `storageState` après login pour scénarios 2–3
- **Pas de golden / RBAC** : scénarios limités OWNER, pas de modification permissions
- **Pas OpenAI live** : fake provider uniquement

## Recommandation

Implémenter d’abord les **testids** produit + commande seed, puis scénario 1 (login→terrain) seul. Scénarios 2–3 une fois le worker Celery E2E stable. Ne pas ajouter à la CI PR — job nightly optionnel.
