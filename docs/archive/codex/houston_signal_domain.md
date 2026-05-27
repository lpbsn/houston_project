# Houston — Signal Domain

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Mama Shelter Nice  
**Documents liés:**  
- `Houston_mvp_cadrage_p0.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_observation_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Signal** de Houston pour le MVP.

Il définit :
- la définition métier d'un Signal ;
- ses règles de création ;
- ses règles d'agrégation ;
- son lifecycle ;
- ses statuts ;
- ses règles multi-domain ;
- ses règles de feed ;
- ses règles de pinning ;
- ses règles d'urgence ;
- ses règles de commentaire ;
- ses relations avec Observations, Actions, médias et events ;
- les règles de permissions liées au Signal ;
- les edge cases ;
- les events MVP ;
- les implications backend/frontend ;
- les tests fonctionnels attendus.

Ce document sert de référence pour Product Owner, Product Designer, Tech Lead, Backend, Frontend et QA.

---

# 2. Définition métier

## 2.1 Définition

Un Signal est une **situation opérationnelle structurée, visible, supervisable et vivante**, générée ou enrichie à partir d'une ou plusieurs Observations.

```txt
Signal
= situation opérationnelle structurée
= unité visible dans le produit
= objet de supervision
= objet de coordination
= point d'entrée vers l'exécution via Actions
```

## 2.2 Ce qu'un Signal n'est pas

Un Signal n'est pas :
- une Observation brute ;
- une Action ;
- une tâche ;
- un ticket classique ;
- une conversation libre ;
- un owner fort unique ;
- une entité créée manuellement directement au MVP.

## 2.3 Rôle dans Houston

Le Signal est la charnière entre :
- la remontée terrain brute ;
- la structuration IA ;
- la supervision manager ;
- la coordination multi-domain ;
- la création d'Actions ;
- la résolution opérationnelle.

```txt
Observation
        ↓
Pipeline IA
        ↓
Signal
        ↓
Actions
        ↓
Résolution
```

## 2.4 Principe central

```txt
Observation = brut invisible UI
Signal = situation opérationnelle visible
Action = responsabilité d'exécution
```

---

# 3. Origine d'un Signal

## 3.1 Signal sans Observation

Décision MVP :

```txt
Un Signal ne peut pas exister sans Observation ou Signal candidat issu d'une Observation.
```

Un Signal doit toujours provenir :
- d'une Observation ;
- ou d'un Signal candidat généré depuis une Observation.

## 3.2 Création manuelle directe

Décision MVP :

```txt
Pas de création manuelle directe de Signal.
```

Tout passe par :

```txt
+Signaler
        ↓
Observation
        ↓
Pipeline IA
        ↓
Signal candidat
        ↓
Signal créé ou agrégé
```

## 3.3 Pourquoi

Cette règle évite :
- de contourner le pipeline IA ;
- de créer deux workflows parallèles ;
- de rendre floue la différence entre Observation et Signal ;
- de produire des Signals sans trace terrain initiale.

---

# 4. Création et agrégation

## 4.1 Création d'un nouveau Signal

Créer un Signal quand le pipeline IA produit un Signal candidat :
- valide ;
- structuré ;
- distinct des Signals actifs existants ;
- suffisamment actionnable ;
- compatible avec les règles backend.

```txt
Signal candidat valide
+
aucun Signal actif similaire
=
nouveau Signal
```

## 4.2 Agrégation à un Signal existant

Agréger si un Signal candidat correspond à un Signal actif similaire.

Critères d'agrégation :
- problème similaire ;
- contexte opérationnel compatible ;
- domains compatibles ;
- établissement identique ;
- Signal cible en statut `open` ou `in_progress`.

```txt
Signal candidat
        ↓
similarité problème + contexte + domains
        ↓
Signal actif existant
        ↓
SignalAggregated
```

## 4.3 Pas d'agrégation sur Signals clôturés

Aggregation uniquement sur :

```txt
open
in_progress
```

Pas d'agrégation sur :

```txt
resolved
canceled
archived
```

## 4.4 Si le même problème revient

Si le même problème revient après `resolved` ou `canceled` :

```txt
Créer un nouveau Signal.
```

Raison :
- une situation clôturée ne doit pas être réactivée implicitement ;
- le retour d'un problème est une nouvelle occurrence opérationnelle ;
- l'historique reste plus propre.

---

# 5. Relation Signal ↔ Observation

## 5.1 Principe

Une Observation reste brute et unique.

Les Signals structurés peuvent être multiples.

```txt
1 Observation
        ↓
0, 1 ou N Signals
```

## 5.2 Max Signals générés

Règle MVP héritée du domaine Observation :

```txt
max_signals_generated_per_observation = 5
```

## 5.3 Table de liaison

Le lien se fait via :

```txt
ObservationSignalLink
├── observation_id
├── signal_id
├── relation_type
├── candidate_signal_index
└── timestamps
```

## 5.4 relation_type

```txt
created
aggregated
split_created
```

## 5.5 Observations invisibles

Les Observations brutes ne sont jamais affichées dans le détail Signal.

```txt
Signal detail
≠ liste d'Observations brutes
```

---

# 6. Structure Signal

## 6.1 Structure recommandée

```txt
Signal
├── id
├── establishment_id
├── title
├── structured_summary
├── detected_domains[]
├── runtime_tags[]
├── urgency
├── pinned
├── status
├── candidate_signal_count
├── created_from_observation_id
├── resolved_at
├── resolved_by_id
├── resolution_reason
├── canceled_at
├── canceled_by_id
├── cancellation_category
├── cancellation_reason
├── archived_at
├── created_at
└── updated_at
```

## 6.2 Champs principaux

| Champ | Description |
|---|---|
| `title` | Résumé court opérationnel |
| `structured_summary` | Synthèse structurée de la situation |
| `detected_domains[]` | Domains détectés / corrigés |
| `runtime_tags[]` | Tags contextuels |
| `urgency` | `normal` ou `high` |
| `pinned` | Pin global établissement, uniquement pour `open` |
| `status` | Lifecycle Signal |
| `candidate_signal_count` | Nombre de Signals candidats agrégés au Signal |
| `created_from_observation_id` | Observation source initiale |
| `resolved_at/by/reason` | Données de résolution |
| `canceled_at/by/category/reason` | Données d'annulation |
| `archived_at` | Sortie du runtime actif |

---

# 7. Status Signal

## 7.1 Status MVP

```txt
open
in_progress
resolved
canceled
archived
```

## 7.2 open

```txt
open = Signal actif, visible, sans Action associée active ou créée.
```

Le Signal est visible et supervisable, mais aucune exécution n'a encore été lancée.

## 7.3 in_progress

```txt
in_progress = Signal avec au moins une Action créée.
```

Le passage est automatique dès qu'une Action est créée.

## 7.4 resolved

```txt
resolved = situation traitée / clôturée opérationnellement.
```

Un Signal devient `resolved` :
- automatiquement quand toutes les Actions liées sont `done` ou `canceled` ;
- ou manuellement par Manager / Director / Owner.

## 7.5 canceled

```txt
canceled = situation annulée / invalide / doublon / non pertinente.
```

Catégories obligatoires :
- `false_alert` ;
- `duplicate` ;
- `invalid` ;
- `other`.

## 7.6 archived

```txt
archived = état historique, hors runtime actif.
```

L'archivage est automatique après délai configurable.

---

# 8. Lifecycle Signal

## 8.1 Lifecycle principal

```txt
open
  ↓ Action created
in_progress
  ↓ all Actions done/canceled OR manual resolution
resolved
  ↓ retention delay
archived
```

## 8.2 Lifecycle alternatif

```txt
open / in_progress
  ↓ cancellation
canceled
  ↓ retention delay
archived
```

## 8.3 Passage open → in_progress

Règle :

```txt
Dès qu'au moins une Action est créée,
Signal passe automatiquement à in_progress.
```

## 8.4 Retour in_progress → open

Règle :

```txt
Si toutes les Actions liées sont canceled
ET qu'aucune Action active n'existe,
Signal revient à open.
```

## 8.5 Résolution automatique

Règle :

```txt
Si toutes les Actions liées sont done ou canceled,
Signal peut passer à resolved.
```

À implémenter avec prudence côté Action Domain pour éviter une résolution prématurée.

## 8.6 Résolution manuelle

Règle :

```txt
Résolution manuelle possible sans Action.
Raison obligatoire.
```

## 8.7 Annulation

Règle :

```txt
Annulation possible par Owner/Director ou Manager des detected_domains.
Raison obligatoire + catégorie obligatoire.
```

## 8.8 Reopen

Décision MVP :

```txt
archived rouvrable = non
canceled rouvrable = non
```

Si le problème revient :

```txt
Créer un nouveau Signal.
```

---

# 9. Domains Signal

## 9.1 Modèle retenu

Un seul champ domain métier :

```txt
detected_domains[]
```

Champs exclus :
- `active_domains[]` ;
- `visibility_domains[]` ;
- `primary_domain`.

## 9.2 detected_domains avec confidence

Chaque domain détecté porte un score.

```json
[
  { "domain": "maintenance", "confidence": 0.91 },
  { "domain": "housekeeping", "confidence": 0.74 }
]
```

## 9.3 Minimum domains

Règle :

```txt
Un Signal doit avoir au moins un detected_domain.
```

## 9.4 Maximum domains MVP

Règle MVP :

```txt
max_detected_domains = 4
```

## 9.5 Pas de primary_domain stocké

Décision :

```txt
Pas de primary_domain en base.
```

L'UI peut afficher en premier le domain avec le score le plus élevé.

## 9.6 Rôle de detected_domains

`detected_domains[]` pilote :
- vue personnelle ;
- filtres ;
- notifications ;
- actionabilité ;
- analytics ;
- corrections IA ;
- supervision manager.

## 9.7 Confidence score

Le score de confidence module :
- le niveau de notification ;
- l'ordre d'affichage des badges ;
- l'analyse qualité IA ;
- les corrections futures.

Il ne crée pas un champ de permission séparé.

---

# 10. Correction manuelle des domains

## 10.1 Qui peut ajouter / retirer un domain

```txt
Owner
Director
Manager
```

## 10.2 Audit obligatoire

Toute correction doit tracer :
- actor_id ;
- previous_domains ;
- new_domains ;
- reason optionnelle ;
- timestamp.

## 10.3 Ajout domain

Règle :

```txt
Ajout domain
→ feed update
→ notification ciblée
→ event SignalDomainAdded
```

Effets :
- le Signal apparaît dans la vue personnelle des users du nouveau domain ;
- les managers concernés peuvent agir ;
- les notifications ciblées sont déclenchées selon règles de notification.

## 10.4 Retrait domain

Règle :

```txt
Retrait domain
→ retrait de la vue personnelle du domain
→ maintien en vue générale
→ event SignalDomainRemoved
```

Effets :
- le Signal reste visible en vue générale ;
- il n'est plus priorisé dans la vue personnelle des users de ce domain ;
- l'analytics IA peut mesurer la sur-détection.

---

# 11. Actionabilité par domain

## 11.1 Owner / Director

```txt
Owner / Director peuvent agir sur tous les Signals de l'établissement.
```

## 11.2 Manager

Règle :

```txt
Manager peut agir sur un Signal
si signal.detected_domains intersecte manager.operational_domains.
```

## 11.3 Manager hors domain

Règle :

```txt
Manager hors domain peut voir/commenter.
Pour agir, il doit avoir le detected_domain.
```

Il peut donc :
- commenter ;
- demander correction ;
- ajouter un detected_domain si pertinent et autorisé ;
- mais ne doit pas piloter sans domain compatible.

## 11.4 Staff

Le Staff peut voir/commenter selon les règles RBAC, mais ne peut pas :
- créer Action ;
- assigner Action ;
- résoudre Signal ;
- annuler Signal ;
- pin Signal ;
- modifier urgency ;
- ajouter/retirer domain.

---

# 12. candidate_signal_count

## 12.1 Décision

Le compteur retenu est :

```txt
candidate_signal_count
```

## 12.2 Définition

```txt
candidate_signal_count = nombre de Signals candidats liés / agrégés au Signal.
```

## 12.3 Incrément

Règle :

```txt
candidate_signal_count += 1
à chaque Signal candidat agrégé au Signal.
```

## 12.4 Note UX

`candidate_signal_count` est un nom technique.

Label UI recommandé :
- “occurrences” ;
- “signalements regroupés” ;
- “regroupements”.

---

# 13. Signal Feed

## 13.1 Ordre MVP

Décision :

```txt
pinned
  ↓
high urgency
  ↓
open
  ↓
in_progress
  ↓
resolved
```

`archived` est hors feed actif.

## 13.2 Vue personnelle / vue générale

### Manager

```txt
Signal Feed par défaut = Signals de ses domains
Signal Feed général = tous les Signals établissement
```

### Staff

```txt
Signal Feed par défaut = Signals de ses domains
Signal Feed général = tous les Signals établissement
```

### Owner / Director

```txt
Signal Feed = tous les Signals établissement
```

## 13.3 Filtres

Filtres domain disponibles en parallèle :
- tous ;
- mes domains ;
- maintenance ;
- housekeeping ;
- security ;
- food_service ;
- guest_experience ;
- pricing ;
- etc.

---

# 14. Pinning

## 14.1 Définition

Le pinning permet de maintenir un Signal informatif en haut du feed.

## 14.2 Règle majeure

Décision :

```txt
Pinned est possible uniquement pour les Signals open.
```

Pourquoi :
- pinning concerne des Signals sans Action ;
- pinning sert à maintenir une information visible ;
- dès qu'une Action existe, le Signal devient une situation d'exécution.

## 14.3 Scope

```txt
Pinning global à l'établissement.
```

## 14.4 Qui peut pin/unpin

```txt
Owner / Director peuvent pin tout Signal.
Manager peut pin les Signals de ses detected_domains.
Staff ne peut pas pin.
```

## 14.5 Micro-règle validée

Si une Action est créée sur un Signal `pinned` et `open` :

```txt
ActionCreated on pinned open Signal
        ↓
SignalUnpinned
        ↓
SignalStatusChanged(open → in_progress)
```

Raison :
- éviter un état incohérent `pinned + in_progress` ;
- respecter la règle “pinning uniquement open”.

---

# 15. Urgency

## 15.1 Niveaux MVP

```txt
normal
high
```

## 15.2 Contrôle

L'urgence est contrôlée manuellement par :
- Manager ;
- Director ;
- Owner.

## 15.3 IA

L'IA peut suggérer une urgence, mais ne l'applique pas automatiquement au MVP.

```txt
AI urgency suggestion = allowed
AI urgency authority = no
```

## 15.4 Events

Changement d'urgence :

```txt
SignalUrgencyChanged
```

---

# 16. SLA

## 16.1 Décision

Pas de SLA au niveau Signal au MVP.

```txt
Signal SLA = Non MVP
```

## 16.2 Pourquoi

Le SLA et l'escalade appartiennent au domaine Action.

```txt
Signal = supervision
Action = responsabilité d'exécution
```

---

# 17. Signal detail

## 17.1 Contenu

Le détail Signal affiche :

```txt
Signal detail
├── titre
├── synthèse structurée
├── detected_domains
├── urgency
├── status
├── candidate_signal_count
├── Actions liées
├── commentaires
├── events
└── médias disponibles
```

## 17.2 Observations

Ne pas afficher :
- texte brut Observation ;
- liste des Observations ;
- page détail Observation.

## 17.3 Médias

Les médias peuvent être affichés comme contexte opérationnel disponible.

Ils proviennent des ObservationMedia liées indirectement.

Ne pas exposer le texte brut Observation associé.

---

# 18. Commentaires Signal

## 18.1 Qui peut commenter

Règle :

```txt
Tous les users qui voient le Signal peuvent commenter.
```

## 18.2 Signal comments dans Actions

Règle :

```txt
Signal comments visibles dans les Actions liées.
```

## 18.3 Action comments

Règle :

```txt
Action comments restent propres à l'Action.
```

Ils ne remontent pas automatiquement dans le Signal.

## 18.4 Event

```txt
SignalCommentAdded
```

---

# 19. Fusion / transfert / séparation

## 19.1 Transfert Signal

Décision MVP :

```txt
Pas de transfert Signal.
```

Correction par :
- ajout de detected_domain ;
- retrait de detected_domain.

## 19.2 Fusion de Signals

Décision MVP :

```txt
Fusion de Signals = Non MVP.
```

Si doublon :
- annuler avec catégorie `duplicate` ;
- ou laisser l'aggregation backend éviter le problème en amont.

## 19.3 Séparation mauvais agrégat

Décision MVP :

```txt
Séparer un Signal mal agrégé = Non MVP.
```

Correction support/admin possible hors UI si nécessaire, mais pas de workflow produit MVP.

---

# 20. Events Signal MVP

## 20.1 Liste validée

```txt
SignalCreated
SignalAggregated
SignalStatusChanged
SignalDomainAdded
SignalDomainRemoved
SignalUrgencyChanged
SignalPinned
SignalUnpinned
SignalResolved
SignalCanceled
SignalArchived
SignalCommentAdded
```

## 20.2 Payload minimal recommandé

### SignalCreated

```json
{
  "event_type": "SignalCreated",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "created_from_observation_id": "uuid",
  "detected_domains": ["maintenance"],
  "status": "open",
  "created_at": "datetime"
}
```

### SignalAggregated

```json
{
  "event_type": "SignalAggregated",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "observation_id": "uuid",
  "candidate_signal_index": 1,
  "candidate_signal_count": 3,
  "created_at": "datetime"
}
```

### SignalStatusChanged

```json
{
  "event_type": "SignalStatusChanged",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "from_status": "open",
  "to_status": "in_progress",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### SignalDomainAdded

```json
{
  "event_type": "SignalDomainAdded",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "domain": "housekeeping",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### SignalDomainRemoved

```json
{
  "event_type": "SignalDomainRemoved",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "domain": "maintenance",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### SignalUrgencyChanged

```json
{
  "event_type": "SignalUrgencyChanged",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "from_urgency": "normal",
  "to_urgency": "high",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### SignalPinned

```json
{
  "event_type": "SignalPinned",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### SignalUnpinned

```json
{
  "event_type": "SignalUnpinned",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "actor_id": "uuid",
  "reason": "action_created",
  "created_at": "datetime"
}
```

### SignalResolved

```json
{
  "event_type": "SignalResolved",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "actor_id": "uuid",
  "resolution_reason": "Intervention completed",
  "created_at": "datetime"
}
```

### SignalCanceled

```json
{
  "event_type": "SignalCanceled",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "actor_id": "uuid",
  "cancellation_category": "duplicate",
  "cancellation_reason": "Already covered by another Signal",
  "created_at": "datetime"
}
```

### SignalArchived

```json
{
  "event_type": "SignalArchived",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "archived_at": "datetime"
}
```

### SignalCommentAdded

```json
{
  "event_type": "SignalCommentAdded",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "comment_id": "uuid",
  "author_id": "uuid",
  "created_at": "datetime"
}
```

---

# 21. API endpoints MVP

## 21.1 Get Signal Feed

```txt
GET /api/v1/signals
```

Query params :
- `view=personal|general`
- `domain=maintenance`
- `status=open`
- `urgency=high`

## 21.2 Get Signal detail

```txt
GET /api/v1/signals/:id
```

Response excludes raw Observations.

## 21.3 Update urgency

```txt
PATCH /api/v1/signals/:id/urgency
```

## 21.4 Add domain

```txt
POST /api/v1/signals/:id/domains
```

## 21.5 Remove domain

```txt
DELETE /api/v1/signals/:id/domains/:domain
```

## 21.6 Pin / unpin

```txt
POST /api/v1/signals/:id/pin
DELETE /api/v1/signals/:id/pin
```

## 21.7 Resolve

```txt
POST /api/v1/signals/:id/resolve
```

## 21.8 Cancel

```txt
POST /api/v1/signals/:id/cancel
```

## 21.9 Add comment

```txt
POST /api/v1/signals/:id/comments
```

---

# 22. Backend services recommandés

## 22.1 Signal creation

```txt
Signals::CreateFromCandidate
```

Responsabilités :
- valider candidate signal ;
- vérifier distinctness ;
- créer Signal ;
- créer ObservationSignalLink ;
- émettre SignalCreated.

## 22.2 Signal aggregation

```txt
Signals::AggregateCandidate
```

Responsabilités :
- trouver Signal actif similaire ;
- vérifier statut open/in_progress ;
- incrémenter candidate_signal_count ;
- créer ObservationSignalLink ;
- émettre SignalAggregated.

## 22.3 Status transition

```txt
Signals::TransitionStatus
```

Responsabilités :
- appliquer règles lifecycle ;
- vérifier permissions ;
- émettre SignalStatusChanged.

## 22.4 Domain correction

```txt
Signals::UpdateDetectedDomains
```

Responsabilités :
- ajouter/retirer domain ;
- audit ;
- notifications ciblées ;
- feed updates ;
- events.

## 22.5 Pinning

```txt
Signals::Pin
Signals::Unpin
```

Responsabilités :
- autoriser uniquement `open` ;
- appliquer scope établissement ;
- émettre events.

## 22.6 Action-created hook

```txt
Signals::HandleActionCreated
```

Responsabilités :
- si Signal `open`, passer `in_progress` ;
- si Signal `pinned`, auto-unpin ;
- émettre `SignalUnpinned` si nécessaire ;
- émettre `SignalStatusChanged`.

---

# 23. Contraintes backend

## 23.1 Establishment scope

Toutes les queries doivent être scoped :

```rb
Signal.where(establishment_id: current_establishment.id)
```

Jamais :

```rb
Signal.all
```

## 23.2 Domain presence

Créer ou mettre à jour un Signal sans `detected_domains` doit échouer.

```txt
detected_domains.size >= 1
```

## 23.3 Domain max

```txt
detected_domains.size <= 4
```

## 23.4 Pinned constraint

```txt
pinned = true allowed only if status = open
```

## 23.5 Archived out of active feed

```txt
status = archived
→ excluded from active feed
```

---

# 24. Edge cases

## 24.1 Action créée sur Signal pinned

```txt
Signal status = open
Signal pinned = true
Action created
        ↓
SignalUnpinned
SignalStatusChanged(open → in_progress)
```

## 24.2 Toutes Actions canceled

```txt
Signal status = in_progress
All actions canceled
No active action remains
        ↓
SignalStatusChanged(in_progress → open)
```

## 24.3 Toutes Actions done/canceled

```txt
All linked Actions done/canceled
        ↓
Signal can become resolved
```

## 24.4 Manager hors domain veut agir

```txt
Manager sees Signal in general view
Manager domains do not intersect signal.detected_domains
        ↓
Can comment
Cannot act
Must add detected_domain if justified
```

## 24.5 Retirer dernier domain

Interdit.

```txt
Signal must keep at least one detected_domain.
```

## 24.6 AI returns too many domains

```txt
If AI returns > 4 domains
Backend keeps top 4 by confidence
OR flags output for correction according to AI Pipeline rules
```

Recommendation MVP :

```txt
keep top 4 by confidence
```

## 24.7 Same problem after resolved

```txt
Candidate matches resolved Signal
        ↓
Do not aggregate
        ↓
Create new Signal
```

## 24.8 Same problem after canceled

```txt
Candidate matches canceled Signal
        ↓
Do not aggregate
        ↓
Create new Signal
```

## 24.9 Duplicate Signal created

MVP correction :

```txt
Cancel duplicate with category duplicate.
No merge UI.
```

---

# 25. Tests fonctionnels MVP

## 25.1 Signal created from candidate

```txt
Given valid Observation
And AI returns valid candidate Signal
And no similar active Signal exists
When processing completes
Then Signal is created
And SignalCreated event is emitted
```

## 25.2 Signal aggregated

```txt
Given existing open Signal
And new candidate Signal matches problem/context/domains
When processing completes
Then candidate is aggregated
And candidate_signal_count increments
And SignalAggregated event is emitted
```

## 25.3 No aggregation on resolved

```txt
Given existing resolved Signal
And new candidate matches it
When processing completes
Then new Signal is created
And no aggregation occurs
```

## 25.4 Open to in_progress

```txt
Given open Signal
When Action is created
Then Signal status becomes in_progress
And SignalStatusChanged event is emitted
```

## 25.5 Pinned auto-unpin

```txt
Given pinned open Signal
When Action is created
Then Signal is unpinned
And Signal becomes in_progress
And SignalUnpinned event is emitted
```

## 25.6 All Actions canceled

```txt
Given in_progress Signal
And all linked Actions are canceled
When no active Action remains
Then Signal returns to open
```

## 25.7 Manual resolution without Action

```txt
Given open Signal without Action
When Manager of detected_domain resolves with reason
Then Signal becomes resolved
And SignalResolved event is emitted
```

## 25.8 Cancel with category

```txt
Given active Signal
When authorized user cancels with category duplicate
Then Signal becomes canceled
And SignalCanceled event is emitted
```

## 25.9 Add domain

```txt
Given Signal
When Manager adds detected_domain
Then domain is added
And SignalDomainAdded is emitted
And feed updates for that domain
```

## 25.10 Remove domain

```txt
Given Signal with multiple domains
When Manager removes one domain
Then Signal leaves personal view for that domain
And remains in general view
And SignalDomainRemoved is emitted
```

## 25.11 Prevent removing last domain

```txt
Given Signal with one detected_domain
When user tries to remove it
Then request is rejected
```

## 25.12 Staff cannot pilot

```txt
Given Staff user
When Staff tries to resolve/pin/cancel Signal
Then request is rejected
```

---

# 26. Décisions validées — index

| Décision | Statut |
|---|---:|
| Signal = situation opérationnelle structurée, visible, supervisable, vivante | Validé |
| Signal doit provenir d'une Observation / Signal candidat | Validé |
| Pas de création manuelle directe de Signal MVP | Validé |
| Création si candidat valide distinct des Signals actifs | Validé |
| Agrégation si candidat similaire à Signal actif compatible | Validé |
| Aggregation uniquement sur open/in_progress | Validé |
| Pas d'aggregation sur resolved/canceled/archived | Validé |
| Même problème après resolved/canceled = nouveau Signal | Validé |
| Status = open/in_progress/resolved/canceled/archived | Validé |
| open = actif visible sans Action | Validé |
| in_progress dès création Action | Validé |
| retour in_progress → open si toutes Actions canceled | Validé |
| resolved si Actions done/canceled ou résolution manuelle | Validé |
| résolution sans Action possible avec raison | Validé |
| Owner/Director résolvent/annulent tous Signals | Validé |
| Manager résout/annule sur ses detected_domains | Validé |
| canceled = faux/invalide/doublon/non pertinent | Validé |
| raison annulation obligatoire + catégorie | Validé |
| archivage automatique après délai configurable | Validé |
| archived/canceled non rouvrables MVP | Validé |
| detected_domains[] seul modèle domains | Validé |
| confidence scores | Validé |
| au moins 1 detected_domain | Validé |
| max 4 detected_domains MVP | Validé |
| pas de primary_domain stocké | Validé |
| detected_domains pilote feed/notifications/actionabilité/analytics | Validé |
| candidate_signal_count | Validé |
| candidate_signal_count incrémenté à chaque candidat agrégé | Validé |
| pas d'Observations brutes dans Signal detail | Validé |
| Signal detail = titre/synthèse/actions/commentaires/events/médias | Validé |
| feed order pinned > high urgency > open > in_progress > resolved | Validé |
| archived hors feed actif | Validé |
| pinning uniquement sur open | Validé |
| pinning global établissement | Validé |
| auto-unpin si Action créée | Validé |
| urgence manuelle normal/high | Validé |
| pas de SLA Signal MVP | Validé |
| tous users voyant Signal peuvent commenter | Validé |
| Signal comments visibles dans Actions liées | Validé |
| Action comments scoped Action | Validé |
| Manager hors domain voit/commente mais ne pilote pas | Validé |
| ajout/retrait detected_domain avec audit | Validé |
| pas de transfert Signal MVP | Validé |
| pas de fusion Signal MVP | Validé |
| pas de séparation mauvais agrégat UI MVP | Validé |
| events Signal MVP | Validé |

---

# 27. Points à traiter dans d'autres domaines

## 27.1 Action Domain

À cadrer :
- création Action ;
- assignation ;
- acceptation ;
- done ;
- pending validation ;
- reopen ;
- cancel ;
- SLA ;
- escalade ;
- impact exact sur Signal resolution.

## 27.2 AI Pipeline Contract

À cadrer :
- schéma candidate_signal ;
- matching / aggregation ;
- confidence thresholds ;
- top 4 domains ;
- top 5 candidates ;
- invalid output ;
- retries.

## 27.3 Notification Matrix

À cadrer :
- qui reçoit SignalCreated ;
- qui reçoit SignalAggregated ;
- notification domain added ;
- notification high urgency ;
- notification comment ;
- push payload minimal.

## 27.4 Media Lifecycle

À cadrer :
- affichage médias Signal ;
- droits d'accès aux médias ;
- retention ;
- signed URLs ;
- suppression.

## 27.5 Event Catalog

À cadrer :
- event persistence ;
- idempotence ;
- correlation_id ;
- causation_id ;
- consumers ;
- retries.

---

# 28. Recommandation finale

Le domaine Signal est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Signal = unité opérationnelle visible.
Observation = brut invisible.
Action = exécution responsable.
```

Le build doit maintenant s'appuyer sur :
- Signals toujours issus d'Observations / candidates ;
- aggregation uniquement sur Signals actifs ;
- lifecycle strict ;
- detected_domains comme unique modèle domain ;
- pinning réservé aux Signals open ;
- urgence manuelle ;
- Signal detail sans Observations brutes ;
- events Signal explicites ;
- interactions Action → Signal bien déterminées.

La prochaine étape logique est le **Action Domain**, car il dépend directement du lifecycle Signal.
