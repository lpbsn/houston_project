# Smoke prod-test Railway

Checklist métier pour valider l’environnement prod-test **Railway** (HTTPS, same-origin) avant pilote externe.

Checklist technique : [`docs/deploy/railway_smoke_checklist.md`](../deploy/railway_smoke_checklist.md). Hub opérateur : [`docs/deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md).

Parcours produit de référence : [`pilot_smoke_checklist.md`](pilot_smoke_checklist.md) — **mêmes étapes**, URLs adaptées ci-dessous.

---

## Préparation Railway

- [ ] Variables conformes à [`railway_variables.md`](../deploy/railway_variables.md) et [`.env.prod-test.example`](../../.env.prod-test.example)
- [ ] `HOUSTON_REGISTRATION_INVITE_CODES` défini (inscription onboarding)
- [ ] `OPENAI_API_KEY` + `HOUSTON_AI_OBSERVATION_PROVIDER=openai` (signaux réalistes)
- [ ] Smoke technique OK : `BASE_URL=https://<railway-domain> ./scripts/smoke/readonly.sh`
- [ ] `celery-worker` et `celery-beat` démarrés (logs Railway)

**Pas de `make web-dev` ni port 5173** — le frontend est servi en build prod sur la même origine HTTPS.

---

## URLs de référence

Remplacer `<railway-domain>` par le hostname public Railway.

| Ressource | URL |
|-----------|-----|
| App (same-origin) | `https://<railway-domain>/` |
| Onboarding | `https://<railway-domain>/onboarding` |
| API health | `https://<railway-domain>/api/v1/health/` |

---

## Parcours produit

Reprendre [`pilot_smoke_checklist.md`](pilot_smoke_checklist.md) § **Parcours produit** sur les URLs ci-dessus :

- [ ] Inscription `/onboarding` avec code invite
- [ ] Login (si compte existant)
- [ ] Organisation + établissement créés / sélectionnés
- [ ] Onboarding manuel v2 complété
- [ ] Établissement activé
- [ ] Observation texte soumise (photo optionnelle)
- [ ] Statut processing → signal dans le feed signaux
- [ ] Action créée depuis le signal
- [ ] Action visible dans l’execution feed

---

## Worker & IA

- [ ] `celery-worker` actif (sinon observations restent `queued`)
- [ ] `celery-beat` actif (horizon checklists, recovery stuck processing)
- [ ] Pipeline OpenAI réel : observation texte → au moins un signal dans le feed

---

## Smoke négatif — upload photo

Comportement actuel documenté ([`report-page.tsx`](../../apps/web/src/features/observations/pages/report-page.tsx) — `canSubmit` exige `photos.every(photo => photo.status === 'ready')`).

**Photo optionnelle** = l’observation peut être envoyée **sans aucune photo**. Dès qu’une photo est ajoutée au brouillon, elle doit être `ready` avant envoi.

Vérifier manuellement sur Railway :

1. **Fichier invalide ou trop lourd** (413 nginx ou 400 API) → message d’erreur visible, submit désactivé
2. **Photo en cours d’upload** (`uploading`) → submit désactivé
3. **Photo en échec** (`failed`) → submit désactivé jusqu’à suppression de la tuile

Ne pas documenter ni appliquer de contournement (submit avec tuile `failed`, ignorer l’erreur, etc.).

---

## Hors scope

- Vitest / `npm test`
- Pagination feed
- RBAC hints UI
