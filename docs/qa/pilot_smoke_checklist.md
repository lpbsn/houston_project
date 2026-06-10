# Pilot smoke checklist

Checklist opérationnelle pour valider une démo ou un pilote local Houston.

## Préparation stack

- [ ] `.env` configuré (`DJANGO_SECRET_KEY`, `HOUSTON_REGISTRATION_INVITE_CODES`)
- [ ] Médias privés OK (volume Docker `private_media` ; dossier local `apps/api/private_media` seulement hors Docker / dépannage)
- [ ] `make bootstrap-dev` OK (inclut `catalog-check` : 14 `CatalogBusinessUnit`, 134 `CatalogActivitySubject`)
- [ ] `docker compose ps` : `postgres`, `redis`, `api`, `celery` **Up**
- [ ] `curl` health → `200` sur http://localhost:8000/api/v1/health/

## Frontend

- [ ] `make web-dev` → http://localhost:5173
- [ ] Pas de conflit port 5173 (`make up` conteneur `web` **ou** `make web-dev`, pas les deux)

## Parcours produit

- [ ] Inscription `/onboarding` avec code invite
- [ ] Login (si compte existant)
- [ ] Organisation + établissement créés / sélectionnés
- [ ] Onboarding manuel v2 complété
- [ ] Établissement activé
- [ ] Observation texte soumise (photo optionnelle)
- [ ] Statut processing → signal dans le feed signaux
- [ ] Action créée depuis le signal
- [ ] Action visible dans l’execution feed

## Worker & IA

- [ ] Service **celery** démarré (sinon observations restent `queued`)
- [ ] (Optionnel) `make up-scheduler` pour celery-beat (matérialisation horizon checklists)
- [ ] (Optionnel) `OPENAI_API_KEY` + `HOUSTON_AI_OBSERVATION_PROVIDER=openai` pour signaux réalistes en manuel

## URLs de référence

| Ressource | URL |
|-----------|-----|
| Frontend | http://localhost:5173 |
| Onboarding | http://localhost:5173/onboarding |
| API health | http://localhost:8000/api/v1/health/ |
| Swagger | http://localhost:8000/api/docs/ |

## Reset local (destructif)

Pour repartir de zéro avant un nouveau pilote :

```bash
make reset-dev-db
make web-install   # si conteneur web Docker utilisé
make web-dev
```

Voir [`INSTALL_MAC.md`](../../INSTALL_MAC.md) et [`fresh_install_validation.md`](fresh_install_validation.md).

## Hors scope

- Vitest / `npm test`
- Pagination feed
- RBAC hints UI
