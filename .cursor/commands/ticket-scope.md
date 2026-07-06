# Ticket Scope

Cadre le ticket avant implémentation.

## Objectif

Transformer la demande en ticket clair, challengé et prêt à implémenter.

Ne code pas dans cette passe, sauf si la demande utilisateur le dit explicitement.

## Consignes

- Lis `AGENTS.md`, `.cursor/rules/` et les fichiers utiles au domaine.
- Lis `apps/api/AGENTS.md` if backend/API is involved
- Lis`apps/web/AGENTS.md` if frontend/PWA is involved
- Analyse le code existant avant de proposer une solution.
- Challenge la demande si elle est trop large, risquée, floue ou mal découpée.
- Garde la scalabilité en tête à chaque niveau : données, API, frontend, cache, realtime, tests, maintenance.
- Ne sois pas exhaustif artificiellement : détaille uniquement ce qui est pertinent.
- Si une décision produit est bloquante, pose une question courte.
- Si l’incertitude est mineure, avance avec une hypothèse explicite.

## Output attendu

### 1. Résumé du ticket

Explique en quelques lignes ce que le ticket cherche à résoudre.

### 2. Cadrage fonctionnel

- Problème identifié :
- Comportement attendu :
- Utilisateurs / rôles concernés :
- Hypothèses :
- Questions bloquantes :

### 3. Scope

In scope :

- ...

Out of scope :

- ...

### 4. Analyse d’impact

Backend :

- modèles / migrations :
- services / selectors :
- API / serializers :
- permissions / RBAC :
- realtime / async / events :
- scalabilité backend :

Frontend :

- pages / routes :
- components :
- hooks / queries :
- cache invalidation :
- generated types :
- mobile / PWA :
- scalabilité frontend :

Tests :

- backend :
- frontend :
- intégration / régression :

Docs :

- docs domaine :
- AGENTS / rules / commands si nécessaire :

### 5. Scalabilité

Analyse spécifiquement :

- volume de données :
- nombre d’utilisateurs / établissements :
- requêtes DB :
- cache / invalidation :
- realtime / events :
- couplage entre domaines :
- maintenabilité à long terme :

### 6. Recommandation

- Solution recommandée :
- Pourquoi :
- Alternatives possibles :
- Alternatives rejetées :
- Risques principaux :

### 7. Definition of Done

Le ticket est terminé quand :

- le comportement attendu est couvert
- les règles métier sont respectées
- les permissions/RBAC sont sécurisées si concernées
- les impacts API/types/frontend sont cohérents
- les impacts cache/realtime sont traités si concernés
- la solution reste scalable et maintenable
- les tests pertinents sont ajoutés ou mis à jour
- les tests ciblés passent
- aucune régression évidente n’est introduite
- la documentation domaine est mise à jour si nécessaire

### 8. Plan d’implémentation

Propose un plan court, ordonné et vérifiable.

1. ...
2. ...
3. ...

### 9. Validation

Commandes ou tests recommandés :

```bash
# Backend
...

# Frontend
...

# Full validation si nécessaire
...
10. Prompt d’implémentation
Écris un prompt court que je pourrai envoyer ensuite pour implémenter ce ticket.
Le prompt doit demander de :
suivre ce cadrage
relire AGENTS.md et .cursor/rules/
implémenter progressivement
éviter les refactors hors scope
respecter la scalabilité
lancer les tests pertinents
reporter les fichiers modifiés et validations
