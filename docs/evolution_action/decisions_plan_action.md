# Decision log — Plan d'action (§26)

Status: `authoritative`  
Lot: -1 (+ compléments Lot 2B — décisions 26.13–26.15)  
Last updated: 2026-06-29  
Sign-off: 2026-06-28 (produit + tech) ; compléments 26.13–26.15 validés Lot 2B (2026-06-29)

## Procédure sign-off

1. Review de ce document et de l'index §26 dans [`besoin_evolution_action.md`](besoin_evolution_action.md).
2. Validation humaine explicite (produit + tech).
3. Après sign-off : passer ce document en statut `authoritative`, dater le sign-off, retirer « en attente » du besoin.

**Sortie Lot -1 :** `Done` (sign-off 2026-06-28).

---

## Tableau des décisions §26

| ID | Sujet | Règle | Lots impactés |
|----|-------|-------|---------------|
| [26.1](#decision-26-1) | Manager contributeur | Voir détail ci-dessous | 2B, 3 |
| [26.2](#decision-26-2) | Assignation cross-scope | Voir détail ci-dessous | 2B |
| [26.3](#decision-26-3) | Pôle assigné sans tâche | Voir détail ci-dessous | 2C, 8 |
| [26.4](#decision-26-4) | Mark-done exécution partagée | Voir détail ci-dessous | 2A, 3 |
| [26.5](#decision-26-5) | Signal lié — sync exécutions | Voir détail ci-dessous | 2D |
| [26.6](#decision-26-6) | Catalogue multi-pôles | Voir détail ci-dessous | 1, 2B |
| [26.7](#decision-26-7) | Tâches modèle multi-pôles | Voir détail ci-dessous | 1, 2A, 2B |
| [26.8](#decision-26-8) | Staff multi-scope (tâches) | Voir détail ci-dessous | 2C |
| [26.9](#decision-26-9) | Retrait pôle impliqué | Voir détail ci-dessous | 2C, 8 |
| [26.10](#decision-26-10) | Contribution `observation_created` | Voir détail ci-dessous | 2C |
| [26.11](#decision-26-11) | Assigné sans tâche | Voir détail ci-dessous | 1, 8 |
| [26.12](#decision-26-12) | Récurrence et contributeurs | Voir détail ci-dessous | 1, 4, 5 |
| [26.13](#decision-26-13) | Création staff (feed execution) | Voir détail ci-dessous | 2B, 3 |
| [26.14](#decision-26-14) | Manager — utilisation catalogue | Voir détail ci-dessous | 2B, 3 |
| [26.15](#decision-26-15) | Cross-pôle — création directe vs catalogue | Voir détail ci-dessous | 2B, 3 |

---

## Décisions détaillées

### Decision 26.1 — Manager contributeur {#decision-26-1}

Le manager contributeur modifie uniquement sa contribution au plan.

**Peut :**

```txt
ajouter des assignés de son scope
CRUD tâches de son pôle
définir la chronologie individuelle des assignés qu'il ajoute dans son scope
```

**Ne peut pas :**

```txt
titre, description, classification globale
pôle d'activité pilote
requires_validation
bascule chronologie commune (chronologie globale)
annulation, réouverture ou validation finale du plan
tâches d'un autre pôle
```

### Decision 26.2 — Assignation cross-scope {#decision-26-2}

Option A :

```txt
Manager du pôle pilote : assignation dans son scope uniquement
Chaque manager contributeur : assignés de son propre scope
Director / Owner : portée globale
```

### Decision 26.3 — Pôle assigné sans tâche {#decision-26-3}

```txt
Le pôle est affiché comme impliqué
Aucun statut de contribution n'est affiché
```

Aligné avec les sections 11, 15 et 16 du besoin.

### Decision 26.4 — Mark-done exécution partagée {#decision-26-4}

Qui peut appeler `mark-done` sur l'exécution globale :

| Acteur | Autorisé |
|--------|----------|
| Assigné du pôle pilote, assigné à l'exécution | Oui |
| Manager du pôle pilote | Oui |
| Director / Owner | Oui |
| Assigné contributeur (autre pôle) | Non — tâches seulement |
| Manager contributeur | Non — global |
| Staff non assigné à l'exécution | Non |

```txt
Pas de workflow accept : l'assignation à l'exécution suffit
Les assignés contributeurs terminent leurs tâches, pas le plan global
```

### Decision 26.5 — Signal lié — sync exécutions {#decision-26-5}

```txt
Actif   = in_progress | pending_validation
Terminal = done | canceled
```

Deux flux distincts : **recalcul automatique** depuis les exécutions, et **résolution manuelle** du signal. Ils ne doivent pas être confondus.

#### Recalcul automatique (exécution → signal)

Déclenché par une mutation d'exécution liée (mark-done, cancel, reopen, etc.).

Résoudre le signal automatiquement quand :

```txt
aucune exécution liée en statut actif
ET au moins une exécution en done
→ signal RESOLVED
```

Si, suite à des annulations côté exécutions (individuelles ou successives), toutes les exécutions liées sont canceled et aucune n'est done :

```txt
signal repasse OPEN
```

Ce cas concerne uniquement le recalcul automatique. Un signal déjà résolu manuellement ne redevient pas OPEN pour cette raison seule.

#### Résolution manuelle (signal → exécutions)

Déclenchée par l'action utilisateur de résoudre le signal.

```txt
toutes les exécutions liées actives passent en canceled
done reste done
canceled reste canceled
signal reste RESOLVED
```

La résolution manuelle du signal ne force jamais une exécution en done. Elle ne crée pas de completion artificielle.

La résolution manuelle **prime** sur le recalcul automatique : tant que le signal est RESOLVED par action manuelle, le fait que toutes les exécutions liées soient canceled ne le fait pas repasser OPEN.

#### Réouverture d'une exécution liée

Si une exécution liée est rouverte après résolution du signal (manuelle ou automatique) :

```txt
signal repasse IN_PROGRESS
```

**Port Lot 2D :** `sync_signal_after_execution_change` pour le recalcul automatique ; flux resolve manuel distinct. Tests obligatoires : auto-resolve (done) ; annulations successives côté exécutions → OPEN si aucune done ; resolve manuel → cancel actives + signal RESOLVED même si toutes canceled ensuite ; reopen exécution → IN_PROGRESS ; résolution manuelle prime sur recalcul auto.

### Decision 26.6 — Catalogue multi-pôles {#decision-26-6}

```txt
Un plan catalogue peut contenir des tâches rattachées à plusieurs pôles
Le catalogue stocke un pôle pilote et des tâches sur différents pôles
Les pôles impliqués sont déduits des tâches à l'utilisation du plan

À la création ou édition du modèle catalogue :
  rattachement explicite d'une tâche à un pôle ≠ pilote → Director / Owner uniquement
  défaut = pôle pilote
```

### Decision 26.7 — Tâches modèle multi-pôles {#decision-26-7}

```txt
Chaque ActionPlanTask a un business_unit obligatoire
Défaut = pôle pilote

Création (formulaire initial, snapshot catalogue) :
  tâche cross-pôle explicite → Director / Owner uniquement

Runtime (exécution en cours) :
  manager pilote → ajouter / modifier / supprimer tâches sur tous les pôles
  manager contributeur → tâches de son pôle seulement
```

Voir aussi l'arbitrage §10 vs §26.6–26.7 ci-dessous.

### Decision 26.8 — Staff multi-scope (tâches) {#decision-26-8}

Règle d'**action sur les tâches** (pas la création de plan — voir [26.13](#decision-26-13)).

```txt
Un staff multi-pôle peut agir sur les tâches de tous ses scopes actifs
Condition : il est assigné à l'exécution ET task.business_unit ∈ ses scopes actifs
```

### Decision 26.9 — Retrait pôle impliqué {#decision-26-9}

Les pôles impliqués sont déduits ; il n'y a pas d'action « supprimer un pôle ».

```txt
Pour retirer un pôle : supprimer ou réaffecter ses assignés ET ses tâches
Si un pôle n'a plus aucun assigné et plus aucune tâche → il disparaît des pôles impliqués
```

### Decision 26.10 — Contribution et observation_created {#decision-26-10}

```txt
done, skipped et observation_created sont des états terminaux pour calculer « Terminé »
```

### Decision 26.11 — Assigné sans tâche {#decision-26-11}

```txt
Un utilisateur peut être assigné à une exécution sans tâche dans son scope
Son pôle apparaît comme impliqué, sans statut de contribution
```

### Decision 26.12 — Récurrence et contributeurs {#decision-26-12}

La récurrence est portée uniquement par le schedule global du plan d'action (`ActionPlanSchedule`).

Les contributeurs ne définissent jamais de récurrence spécifique. Il n'existe pas de `recurrence_rule` par pôle contributeur.

À chaque occurrence générée, les contributeurs participent à l'exécution en cours s'ils ont :

```txt
au moins un assigné dans leur pôle
OU
au moins une tâche rattachée à leur pôle
```

Ils ne créent pas d'occurrence autonome.

Une exécution reste l'unité métier globale pour :

```txt
le feed
le statut global
la validation finale
le signal lié
les commentaires
les tâches snapshotées
les contributions calculées
```

Les pôles contributeurs peuvent avoir des tâches, assignés ou deadlines dans l'exécution, mais pas de fréquence propre.

Si un pôle doit intervenir selon une fréquence différente, il faut créer un autre plan d'action.

**Cohérence besoin :**

```txt
§9 chronologie commune / individuelle → horaires et regroupement d'assignés par occurrence, pas une récurrence par pôle
§9 exécution individuelle ou partagée → occurrences générées par le schedule global
§11 pôles impliqués → déduits des assignés et tâches par exécution
§15 contribution → calculée par pôle à partir des tâches snapshotées sur l'exécution
§8 validation finale → une seule par exécution, pôle pilote / Director / Owner
```

La chronologie individuelle (décision [26.1](#decision-26-1), §9) définit des horaires par assigné dans le cadre d'une occurrence ; ce n'est pas une récurrence contributeur.

### Decision 26.13 — Création staff (feed execution) {#decision-26-13}

Complément Lot 2B (A1). Le staff **ne crée pas** de plan via signal, catalogue, ni enregistrement bibliothèque.

**Chemin autorisé :** création ponctuelle depuis le feed execution (`create_action_plan_with_execution`, sans signal, `is_reusable=false`).

**Contraintes obligatoires :**

```txt
pilot_business_unit ∈ scope staff
assigné uniquement à lui-même, sur le pôle pilote
pas de pôle contributeur (assignés et tâches sur pilot_business_unit uniquement)
tâches uniquement dans son scope (= pôle pilote, pas de cross-pôle)
requires_validation = false
```

**Interdit :**

```txt
création liée à un signal
création ou enregistrement catalogue (is_reusable=true, catalog_status actif)
requires_validation = true
multi-assignés ou assignation d'autres membres
```

### Decision 26.14 — Manager — utilisation catalogue {#decision-26-14}

Complément Lot 2B (A2).

Un manager peut **utiliser** un plan catalogue (`can_use_action_plan` / `create_execution_from_action_plan`) si le **pôle pilote** du modèle est dans son scope, **même si certaines tâches du modèle sont sur des pôles hors de son scope**.

```txt
Scope requis : pilot_business_unit ∈ scope manager
Tâches catalogue hors scope manager : héritées telles quelles (snapshot) — pas de droit de modification à l'utilisation
Staff : pas d'accès catalogue (utilisation ni création)
```

### Decision 26.15 — Cross-pôle — création directe vs catalogue {#decision-26-15}

Complément Lot 2B (A3). Précise [26.6](#decision-26-6) et [26.7](#decision-26-7) pour le RBAC à la création.

| Contexte | Tâche sur pôle ≠ pilote (`task.business_unit ≠ pilot_business_unit`) |
|----------|-----------------------------------------------------------------------|
| **Création directe** (`create_action_plan`, `create_action_plan_with_execution` hors catalogue) | Director / Owner **uniquement** |
| **Utilisation catalogue** (`create_execution_from_action_plan`) | Tâches déjà présentes dans le modèle catalogue — snapshot autorisé sans re-vérification admin |

```txt
Création directe : manager ne peut pas ajouter de tâche cross-pôle
Catalogue : le manager in-scope sur le pilote hérite les tâches multi-pôles du modèle
Assignation §26.2 : toujours appliquée sur les assignés ajoutés à l'exécution, y compris depuis catalogue
```

---

## Arbitrages {#arbitrages}

### §10 vs §26.6–26.7 — Création vs runtime

**Choix retenu :** scinder création et runtime.

| Phase | Qui peut rattacher une tâche à un pôle ≠ pilote |
|-------|--------------------------------------------------|
| Création / édition catalogue ou formulaire initial | Director / Owner |
| Runtime (exécution en cours) | Manager pilote (tous pôles) ; manager contributeur (son pôle) |

Le besoin §10 (« ajouter des tâches sur tous les pôles ») s'applique au **runtime**. Les restrictions cross-pôle à la **création** sont dans les décisions [26.6](#decision-26-6), [26.7](#decision-26-7) et [26.15](#decision-26-15) (directe vs catalogue).

---

## Chronologie (26.1)

Frontière « chronologie globale » vs « chronologie individuelle » :

```txt
Chronologie globale = bascule chronologie commune, paramètres partagés au niveau plan/exécution
Chronologie individuelle = dates/horaires par assigné que le manager contributeur définit pour les membres de son scope
```

La section 9 du besoin (assignation et chronologie) reste inchangée.
