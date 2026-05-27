# Houston — Observation Domain

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Mama Shelter Nice  
**Documents liés:**  
- `Houston_mvp_cadrage_p0.md`
- `Houston_rbac_permissions_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Observation** de Houston pour le MVP.

Il définit :
- la définition métier d'une Observation ;
- les inputs MVP ;
- les règles de validation ;
- le lifecycle ;
- les statuts ;
- la relation avec le pipeline IA ;
- la relation avec les Signals ;
- la relation avec les Checklists ;
- la relation avec les médias ;
- les règles de visibilité ;
- les events MVP ;
- les implications backend/frontend ;
- les edge cases ;
- les tests fonctionnels attendus.

Ce document sert de référence pour Product Owner, Product Designer, Tech Lead, Backend, Frontend et QA.

---

# 2. Définition métier

## 2.1 Définition

Une Observation est une **remontée terrain brute**, validée par l'utilisateur, persistée immédiatement, et non modifiable après envoi.

```txt
Observation
= Raw Field Input
= remontée terrain brute
= input validé par l'utilisateur
= trace initiale avant structuration opérationnelle
```

## 2.2 Ce qu'une Observation n'est pas

Une Observation n'est pas :
- un Signal ;
- une Action ;
- une tâche ;
- un commentaire ;
- une conversation ;
- une entité éditable de coordination ;
- un objet visible dans l'interface produit standard.

## 2.3 Rôle dans Houston

L'Observation est le point d'entrée terrain.

```txt
Observation
        ↓
Pipeline IA
        ↓
Signal créé / Signal candidat agrégé / aucun Signal créé
        ↓
Coordination opérationnelle via Signal
```

## 2.4 Principe d'immutabilité

Une fois soumise :

```txt
Observation non modifiable
Observation non supprimable par l'utilisateur
Observation conservée comme trace brute
```

Toute correction opérationnelle doit se faire via un Signal, une Action, un commentaire, une nouvelle Observation, ou une correction manager sur le Signal.

---

# 3. Inputs MVP

## 3.1 Inputs autorisés

```txt
Observation input
├── texte saisi
OU
├── audio transcrit puis validé
+
├── photos optionnelles
+
└── contexte checklist optionnel
```

## 3.2 Texte

Le texte est l'input canonique du pipeline IA.

Il peut venir :
- d'une saisie directe ;
- d'une transcription audio validée.

## 3.3 Audio

L'audio fait partie du MVP, mais n'est pas obligatoire.

L'audio est un mécanisme UX, pas une donnée métier durable.

```txt
Audio
        ↓
Speech-to-text
        ↓
Transcription affichée à l'utilisateur
        ↓
Utilisateur valide / corrige
        ↓
Texte persisté dans Observation
        ↓
Audio supprimé
```

## 3.4 Photos

Les photos sont optionnelles.

Elles servent :
- au contexte humain ;
- à la preuve visuelle ;
- à l'aide à la résolution ;
- à la supervision terrain.

Elles ne sont pas obligatoires pour créer une Observation.

## 3.5 Contexte checklist

Une Observation peut être créée depuis une tâche de checklist.

Dans ce cas, elle peut porter :
- `checklist_execution_id` ;
- `checklist_task_execution_id` ;
- `operational_unit_id` ;
- `source = checklist`.

---

# 4. Règles de validité

## 4.1 Observation valide

Une Observation valide doit contenir :

```txt
texte saisi
OU
transcription audio validée
```

Les photos seules sont interdites.

## 4.2 Photo-only interdit

```txt
Observation avec photos uniquement = invalide
```

Raison :
- le pipeline IA travaille sur un input textuel ;
- une image seule ne fournit pas de contexte métier fiable au MVP ;
- l'IA image est hors MVP.

## 4.3 Longueur minimale

Règle MVP :

```txt
minimum_text_length = 10 caractères
```

Exception :

```txt
Si Observation issue d'une checklist,
le contexte task peut suffire avec un texte plus court.
```

Exemple :

```txt
Checklist task: "Vérifier chambre froide"
User input: "HS"
```

## 4.4 Longueur maximale

Règle MVP :

```txt
maximum_text_length = 1000 caractères
```

Raison :
- garder les inputs terrain concis ;
- limiter le bruit ;
- maîtriser les coûts IA ;
- simplifier l'UX mobile.

## 4.5 Operational Unit

L'utilisateur ne doit pas être forcé à choisir une Operational Unit.

```txt
Operational Unit demandée à l'utilisateur = Non MVP
```

Si disponible via checklist ou contexte :
- elle peut être attachée automatiquement ;
- elle peut enrichir le pipeline IA.

## 4.6 Urgence déclarative

L'utilisateur ne déclare pas l'urgence au MVP.

```txt
User-declared urgency = Non MVP
```

L'urgence est déduite par le pipeline IA, validée par le backend, puis modifiable côté manager selon le domaine Signal.

## 4.7 Signalement anonyme

Le signalement anonyme est hors MVP.

```txt
Anonymous reporting = Non MVP
```

Raison :
- besoin de traçabilité opérationnelle ;
- contexte terrain utile ;
- accountability nécessaire dans l'exécution.

---

# 5. Lifecycle Observation

## 5.1 Lifecycle simplifié

```txt
Draft frontend only
        ↓
Submit
        ↓
Persisted
        ↓
Queued for AI
        ↓
Processing
        ↓
Processed / Retry / Failed
        ↓
Outcome
```

## 5.2 Draft

Le draft est uniquement frontend.

```txt
Draft
├── local frontend only
├── non persisté backend
├── supprimé après submit réussi
└── pas de draft backend MVP
```

## 5.3 Submit

Au submit :
- l'Observation est validée côté frontend ;
- elle est validée côté backend ;
- elle est persistée immédiatement ;
- les médias temporaires sont liés ;
- un event `ObservationCreated` est émis ;
- un processing IA est créé/queued.

## 5.4 Après submit

Après submit :

```txt
Observation persistée
Observation non modifiable
Observation non annulable
Observation non supprimable par l'utilisateur
```

## 5.5 Annulation

L'annulation est possible uniquement avant submit.

```txt
Avant submit : cancel possible
Après submit : cancel impossible
```

---

# 6. Statuts

## 6.1 Observation status

L'Observation reste volontairement simple.

```txt
Observation
├── draft frontend only
└── submitted / persisted
```

Le statut `draft` n'existe pas en base.

## 6.2 ObservationProcessing status

Le processing technique est séparé.

```txt
ObservationProcessing
├── queued
├── processing
├── processed
├── retrying
└── failed
```

## 6.3 Pourquoi séparer Observation et Processing

L'Observation représente la donnée brute métier.

Le Processing représente l'orchestration technique :
- queue ;
- worker ;
- retry ;
- erreur ;
- timeout ;
- résultat IA ;
- validation backend.

Cette séparation évite de polluer l'Observation avec des états techniques.

## 6.4 Statut UX utilisateur

L'utilisateur voit uniquement un statut simplifié.

```txt
Analyse en cours
Signal créé
X Signals créés
Signalement ajouté à un Signal existant
Observation non exploitable
Analyse temporairement impossible
```

Les statuts techniques ne sont pas exposés tels quels.

---

# 7. Outcomes Observation

## 7.1 Outcomes possibles

Une Observation traitée peut produire :

```txt
ObservationOutcome
├── signal_created
├── multiple_signals_created
├── signal_aggregated
├── no_signal_created
└── processing_failed
```

## 7.2 Signal créé

Cas :

```txt
Observation
        ↓
Pipeline IA
        ↓
Nouveau Signal créé
```

Message UX :

```txt
Signal créé
```

## 7.3 Plusieurs Signals créés

Une Observation peut contenir plusieurs situations opérationnelles.

Cas :

```txt
Observation
        ↓
Pipeline IA
        ↓
Split
        ↓
2 à 5 Signals créés
```

Message UX :

```txt
X Signals créés
```

## 7.4 Signal candidat agrégé

Correction importante :

Ce n'est pas l'Observation entière qui s'agrège.

Le flow exact est :

```txt
Observation envoyée
        ↓
Pipeline IA
        ↓
Signal candidat généré
        ↓
Backend détecte un Signal existant similaire
        ↓
Signal candidat agrégé au Signal existant
        ↓
Observation liée au Signal existant
```

Message UX :

```txt
Signalement ajouté à un Signal existant
```

## 7.5 Aucun Signal créé

Décision finale :

```txt
no_signal_created est conservé comme outcome normal.
```

Cas :

```txt
Observation
        ↓
Pipeline IA
        ↓
Backend validation
        ↓
Aucun Signal opérationnel nécessaire
```

Message UX :

```txt
Observation non exploitable
```

ou :

```txt
Aucun Signal nécessaire
```

## 7.6 Processing failed

Cas :
- erreur IA ;
- timeout ;
- JSON invalide ;
- worker failed ;
- backend validation impossible ;
- erreur stockage/liaison.

Message UX :

```txt
Analyse temporairement impossible. Réessai en cours.
```

---

# 8. Relation Observation ↔ Signal

## 8.1 Principe

Une Observation reste brute et unique.

Les Signals structurés peuvent être multiples.

```txt
1 Observation
        ↓
0, 1 ou N Signals
```

## 8.2 Maximum de Signals

Règle MVP :

```txt
max_signals_generated_per_observation = 5
```

## 8.3 Relation multiple

Une Observation peut être liée à plusieurs Signals :
- Signals qu'elle génère ;
- Signals existants auxquels ses Signals candidats sont agrégés.

## 8.4 Pas de `signal_id` direct

Ne pas mettre `signal_id` directement dans `observations`.

Mauvais modèle :

```txt
Observation
└── signal_id
```

Pourquoi :
- bloque le multi-Signal ;
- ne distingue pas création / agrégation ;
- force une relation 1:1 fausse ;
- ne permet pas de tracer le split.

## 8.5 Table de liaison recommandée

```txt
ObservationSignalLink
├── id
├── observation_id
├── signal_id
├── relation_type
├── candidate_signal_index
├── created_at
└── updated_at
```

## 8.6 relation_type

```txt
relation_type
├── created
├── aggregated
└── split_created
```

### created

Le Signal a été créé directement depuis l'Observation.

### aggregated

Un Signal candidat issu de l'Observation a été agrégé à un Signal existant.

### split_created

L'Observation a été splittée et ce Signal fait partie des Signals créés.

## 8.7 candidate_signal_index

Optionnel mais recommandé.

Permet de tracer quel Signal candidat a produit quel lien.

Exemple :

```txt
Observation #123
├── candidate_signal_index 1 → Signal #456 created
├── candidate_signal_index 2 → Signal #789 aggregated
└── candidate_signal_index 3 → Signal #901 split_created
```

---

# 9. Visibilité Observation

## 9.1 Décision produit

Les Observations brutes ne sont pas visibles dans l'interface produit.

```txt
Raw Observations
= non visibles dans l'UI produit
= accessibles uniquement en base / requête admin technique
```

## 9.2 Pas de détail Observation

Il n'y a pas de page détail Observation au MVP.

```txt
Observation detail page = Non MVP
```

## 9.3 Pas d'Observation dans le détail Signal

Le détail Signal ne doit pas afficher les Observations brutes.

```txt
Signal detail
≠ liste des Observations brutes
```

## 9.4 Pourquoi

Le produit doit rester centré sur les Signals comme unité opérationnelle visible.

```txt
Observation = brut invisible UI
Signal = unité opérationnelle visible
```

Cela évite :
- surcharge d'information ;
- exposition de contenu brut potentiellement mal formulé ;
- confusion entre remontée brute et situation structurée ;
- bruit dans le détail Signal.

## 9.5 Accès technique

Les Observations restent accessibles :
- en base de données ;
- via requête admin technique ;
- pour debug ;
- pour audit ;
- pour qualité IA ;
- pour investigation support.

Cet accès doit être contrôlé hors UI produit standard.

---

# 10. Relation avec Checklist

## 10.1 Principe

Une Observation peut être créée depuis une checklist task.

Dans ce cas, elle est contextualisée.

## 10.2 Champs recommandés

```txt
Observation
├── checklist_execution_id optional
├── checklist_task_execution_id optional
├── operational_unit_id optional
└── source = direct | checklist
```

## 10.3 Source

```txt
source
├── direct
└── checklist
```

### direct

Observation créée depuis le bouton ou flow standard de signalement.

### checklist

Observation créée depuis une checklist task.

## 10.4 Rôle du contexte checklist

Le contexte checklist aide à :
- comprendre une phrase courte ;
- contextualiser l'anomalie ;
- améliorer le routing ;
- améliorer le split ;
- améliorer l'agrégation ;
- relier l'anomalie à une routine opérationnelle.

## 10.5 Exemple

```txt
Checklist: Ouverture Restaurant
Task: Vérifier chambre froide
User input: "température trop haute"
        ↓
Observation context:
- checklist_execution_id
- checklist_task_execution_id
- task label
- operational_unit_id
        ↓
Pipeline IA
        ↓
Signal Maintenance / Food Safety
```

---

# 11. Relation avec médias

## 11.1 Principe

Les médias appartiennent à l'Observation.

```txt
ObservationMedia belongs_to Observation
```

Le Signal affiche les médias indirectement via les Observations liées si nécessaire dans les composants de supervision, mais les Observations brutes ne sont pas exposées dans le détail Signal MVP.

## 11.2 Nombre de photos

Règle MVP :

```txt
max_photos_per_observation = 3
```

## 11.3 Upload

Workflow validé :

```txt
Temporary upload before send
        ↓
Observation submit
        ↓
Media linked to Observation
        ↓
Cleanup orphan uploads
```

## 11.4 Formats

Formats recommandés MVP :
- JPEG ;
- JPG ;
- PNG ;
- HEIC si mobile iOS supporté.

## 11.5 Taille

À cadrer dans le domaine Upload / Media Lifecycle.

Recommandation technique future :
- compression client-side ;
- taille cible 1 à 2 MB ;
- taille max originale 10 MB.

## 11.6 IA image

L'analyse IA des images est hors MVP.

```txt
Image AI analysis = Post-MVP
```

---

# 12. Audio / transcription

## 12.1 Principe

L'audio n'est pas conservé.

```txt
Audio deleted after transcription
Only validated transcription persists
```

## 12.2 Workflow

```txt
User records audio
        ↓
Temporary audio upload / local processing
        ↓
Speech-to-text
        ↓
Transcription displayed
        ↓
User validates / edits
        ↓
Observation submitted
        ↓
Audio deleted
```

## 12.3 Donnée persistée

Seule la transcription validée est persistée dans l'Observation.

```txt
Observation.raw_text = validated_transcription
```

## 12.4 Échec transcription

Si transcription échoue :
- l'utilisateur peut réessayer ;
- ou basculer en saisie texte.

Règle MVP :

```txt
Transcription failure must not block text reporting.
```

---

# 13. Draft frontend

## 13.1 Décision

Le draft est local frontend uniquement.

```txt
Draft local frontend
Pas de draft backend MVP
```

## 13.2 Suppression

Le draft est supprimé après submit réussi.

## 13.3 Persistance

À cadrer côté frontend/PWA :
- survit au refresh ou non ;
- survit à la fermeture app ou non ;
- stockage local ;
- nettoyage.

Décision MVP actuelle :

```txt
No backend draft.
```

---

# 14. Modèle de données recommandé

## 14.1 observations

```txt
observations
├── id UUID
├── establishment_id UUID
├── author_id UUID
├── source enum
│   ├── direct
│   └── checklist
├── raw_text text
├── checklist_execution_id UUID nullable
├── checklist_task_execution_id UUID nullable
├── operational_unit_id UUID nullable
├── submitted_at datetime
├── soft_deleted_at datetime nullable
├── soft_deleted_by_id UUID nullable
├── soft_delete_reason text nullable
├── created_at datetime
└── updated_at datetime
```

## 14.2 observation_processings

```txt
observation_processings
├── id UUID
├── observation_id UUID
├── status enum
│   ├── queued
│   ├── processing
│   ├── processed
│   ├── retrying
│   └── failed
├── outcome enum nullable
│   ├── signal_created
│   ├── multiple_signals_created
│   ├── signal_aggregated
│   ├── no_signal_created
│   └── processing_failed
├── attempts integer
├── last_error_code string nullable
├── last_error_message text nullable
├── queued_at datetime nullable
├── processing_started_at datetime nullable
├── processed_at datetime nullable
├── failed_at datetime nullable
├── created_at datetime
└── updated_at datetime
```

## 14.3 observation_signal_links

```txt
observation_signal_links
├── id UUID
├── observation_id UUID
├── signal_id UUID
├── relation_type enum
│   ├── created
│   ├── aggregated
│   └── split_created
├── candidate_signal_index integer nullable
├── created_at datetime
└── updated_at datetime
```

## 14.4 observation_media

```txt
observation_media
├── id UUID
├── observation_id UUID
├── storage_key string
├── mime_type string
├── file_size integer
├── original_filename string nullable
├── uploaded_by_id UUID
├── retention_status string
├── scheduled_deletion_at datetime nullable
├── created_at datetime
└── updated_at datetime
```

## 14.5 Contraintes importantes

### Text presence

```txt
raw_text required
```

### Text length

```txt
raw_text length <= 1000
raw_text length >= 10 except checklist context supported
```

### Media count

```txt
max 3 observation_media per observation
```

### Establishment scope

Tous les modèles doivent être establishment-scoped directement ou indirectement.

---

# 15. Events MVP

## 15.1 Events validés

```txt
ObservationCreated
ObservationMediaLinked
ObservationQueuedForAI
ObservationProcessingStarted
ObservationProcessingSucceeded
ObservationProcessingFailed
ObservationLinkedToSignal
ObservationMarkedNotActionable
```

## 15.2 Note sur ObservationMarkedNotActionable

Même si `no_signal_created` est conservé, l'event `ObservationMarkedNotActionable` peut être utilisé pour tracer un outcome non exploitable.

Règle :

```txt
ObservationMarkedNotActionable
= event métier quand outcome = no_signal_created
OU outcome = not_actionable si ce statut est conservé ultérieurement
```

## 15.3 Payload minimal recommandé

### ObservationCreated

```json
{
  "event_type": "ObservationCreated",
  "observation_id": "uuid",
  "establishment_id": "uuid",
  "author_id": "uuid",
  "source": "direct",
  "has_media": true,
  "media_count": 2,
  "created_at": "datetime"
}
```

### ObservationQueuedForAI

```json
{
  "event_type": "ObservationQueuedForAI",
  "observation_id": "uuid",
  "establishment_id": "uuid",
  "queued_at": "datetime"
}
```

### ObservationProcessingSucceeded

```json
{
  "event_type": "ObservationProcessingSucceeded",
  "observation_id": "uuid",
  "establishment_id": "uuid",
  "outcome": "multiple_signals_created",
  "signals_count": 2,
  "processed_at": "datetime"
}
```

### ObservationLinkedToSignal

```json
{
  "event_type": "ObservationLinkedToSignal",
  "observation_id": "uuid",
  "signal_id": "uuid",
  "relation_type": "aggregated",
  "candidate_signal_index": 1,
  "establishment_id": "uuid",
  "created_at": "datetime"
}
```

### ObservationProcessingFailed

```json
{
  "event_type": "ObservationProcessingFailed",
  "observation_id": "uuid",
  "establishment_id": "uuid",
  "error_code": "ai_timeout",
  "attempts": 2,
  "failed_at": "datetime"
}
```

---

# 16. API endpoints MVP

## 16.1 Create Observation

```txt
POST /api/v1/observations
```

### Body

```json
{
  "raw_text": "Fuite d'eau devant la chambre 312",
  "source": "direct",
  "temporary_media_ids": ["uuid1", "uuid2"]
}
```

### Checklist context body

```json
{
  "raw_text": "Température trop haute",
  "source": "checklist",
  "checklist_execution_id": "uuid",
  "checklist_task_execution_id": "uuid",
  "operational_unit_id": "uuid",
  "temporary_media_ids": []
}
```

### Response

```json
{
  "observation_id": "uuid",
  "processing_status": "queued",
  "ux_status": "analysis_pending"
}
```

## 16.2 Get Observation Processing Status

Optionnel MVP.

```txt
GET /api/v1/observations/:id/processing_status
```

### Response

```json
{
  "observation_id": "uuid",
  "status": "processed",
  "outcome": "signal_created",
  "signals_count": 1,
  "ux_message": "Signal créé"
}
```

## 16.3 No Observation detail endpoint for product UI

Il n'y a pas d'endpoint produit standard pour consulter une Observation brute.

Accès admin/support à traiter séparément.

---

# 17. Backend services recommandés

## 17.1 Create service

```txt
Observations::Create
```

Responsabilités :
- valider input ;
- vérifier author membership ;
- vérifier establishment context ;
- créer Observation ;
- lier médias temporaires ;
- créer ObservationProcessing ;
- émettre ObservationCreated ;
- émettre ObservationQueuedForAI.

## 17.2 Queue service

```txt
Observations::QueueForAI
```

Responsabilités :
- mettre en queue ;
- idempotence ;
- marquer processing queued.

## 17.3 Processing worker

```txt
Observations::ProcessWithAIJob
```

Responsabilités :
- charger Observation ;
- charger context établissement ;
- charger context checklist si présent ;
- appeler pipeline IA ;
- valider output ;
- créer / agréger Signals ;
- créer ObservationSignalLinks ;
- définir outcome ;
- émettre events.

## 17.4 Media link service

```txt
Observations::AttachMedia
```

Responsabilités :
- vérifier ownership temporary uploads ;
- vérifier max 3 ;
- créer ObservationMedia ;
- cleanup invalid uploads.

## 17.5 Soft delete admin service

```txt
Observations::AdminSoftDelete
```

Responsabilités :
- réservé admin technique ;
- soft delete ;
- audit ;
- jamais utilisé par user standard.

---

# 18. Frontend UX rules

## 18.1 Submit flow

```txt
User enters text OR validates transcription
        ↓
Optional photos
        ↓
Submit
        ↓
Immediate feedback
        ↓
Analysis pending
        ↓
Result message
```

## 18.2 Messages UX

| Situation | Message |
|---|---|
| Submit réussi | Signalement envoyé |
| Processing queued | Analyse en cours |
| 1 Signal créé | Signal créé |
| Plusieurs Signals créés | X Signals créés |
| Signal agrégé | Signalement ajouté à un Signal existant |
| Aucun Signal créé | Observation non exploitable |
| Processing failed | Analyse temporairement impossible. Réessai en cours. |
| Photo-only | Ajoutez une description ou utilisez l'audio |
| Texte trop court | Ajoutez quelques détails |
| Texte trop long | Votre signalement dépasse 1 000 caractères |

## 18.3 UI constraints

- ne pas montrer les statuts techniques ;
- ne pas afficher de page détail Observation ;
- ne pas afficher les Observations brutes dans Signal detail ;
- montrer uniquement le résultat opérationnel côté Signal.

---

# 19. Permissions

## 19.1 Création

Tous les rôles peuvent créer une Observation.

```txt
Owner: yes
Director: yes
Manager: yes
Staff: yes
```

## 19.2 Lecture

Les Observations brutes ne sont pas visibles dans l'UI produit.

```txt
Product UI read access = no
```

## 19.3 Admin technique

Les Observations peuvent être consultées :
- en base ;
- via requête admin technique ;
- dans un outil interne support/admin si créé plus tard.

## 19.4 Suppression

Pas de suppression utilisateur standard.

Soft delete admin uniquement.

```txt
Soft delete requires:
- admin actor
- reason
- audit log
```

---

# 20. Edge cases

## 20.1 Photo-only

```txt
Input photos only
→ invalid
→ user must add text or audio transcription
```

## 20.2 Text too short

```txt
raw_text < 10 chars
AND source != checklist with sufficient context
→ invalid
```

## 20.3 Text too long

```txt
raw_text > 1000 chars
→ invalid
```

## 20.4 Audio transcription failed

```txt
transcription failed
→ user can retry
OR switch to text
```

## 20.5 Upload media failed

```txt
media upload failed
→ user can submit without photo
OR retry upload
```

## 20.6 AI timeout

```txt
ObservationProcessing = retrying
attempts += 1
user sees simplified message
```

## 20.7 AI invalid JSON

```txt
ObservationProcessing = retrying or failed
last_error_code = invalid_ai_output
admin visible
```

## 20.8 Too many Signals

```txt
AI returns > 5 candidate signals
→ backend keeps max 5
OR marks output invalid
```

Recommendation MVP :

```txt
backend keeps top 5 by confidence/actionability
```

## 20.9 No Signal created

```txt
ObservationProcessing = processed
outcome = no_signal_created
user sees "Observation non exploitable"
```

## 20.10 User closes app after submit

```txt
Observation already persisted
processing continues async
user can see result through feed/notification/status if implemented
```

## 20.11 Orphan temporary uploads

```txt
temporary upload not linked to Observation
→ cleanup job deletes after TTL
```

---

# 21. Tests fonctionnels MVP

## 21.1 Création Observation texte

```txt
Given active user
When user submits valid text
Then Observation is persisted
And ObservationProcessing is queued
And ObservationCreated event is emitted
```

## 21.2 Photo-only rejected

```txt
Given user uploaded photos
When user submits without text or transcription
Then request is rejected
And no Observation is created
```

## 21.3 Audio transcription persisted as text

```txt
Given user records audio
And transcription succeeds
And user validates transcription
When user submits
Then Observation.raw_text equals validated transcription
And audio is deleted
```

## 21.4 Max 3 photos

```txt
Given user attaches 4 photos
When user submits
Then request is rejected
Or frontend prevents submit
```

## 21.5 Checklist context

```txt
Given user reports anomaly from checklist task
When Observation is submitted
Then checklist_execution_id is stored
And checklist_task_execution_id is stored
And source = checklist
```

## 21.6 Observation non editable

```txt
Given submitted Observation
When user attempts update
Then request is rejected
```

## 21.7 User cannot delete Observation

```txt
Given submitted Observation
When standard user attempts delete
Then request is rejected
```

## 21.8 Admin soft delete

```txt
Given admin actor
When admin soft deletes Observation with reason
Then soft_deleted_at is set
And audit event is created
```

## 21.9 Multiple Signals

```txt
Given AI returns multiple valid candidate signals
When backend processes Observation
Then up to 5 Signals are created/aggregated
And ObservationSignalLinks are created
```

## 21.10 No Signal created

```txt
Given AI/backend decides no Signal is needed
When processing completes
Then ObservationProcessing.status = processed
And outcome = no_signal_created
```

---

# 22. Décisions validées — index

| Décision | Statut |
|---|---:|
| Observation = remontée terrain brute | Validé |
| Observation validée par l'utilisateur | Validé |
| Observation persistée immédiatement | Validé |
| Observation non modifiable après envoi | Validé |
| Texte OU transcription validée requis | Validé |
| Photos optionnelles | Validé |
| Photos seules interdites | Validé |
| Minimum 10 caractères | Validé |
| Exception checklist texte court | Validé |
| Maximum 1 000 caractères | Validé |
| Pas de suppression utilisateur standard | Validé |
| Soft delete admin + audit | Validé |
| Annulation avant submit uniquement | Validé |
| Statuts UX simplifiés | Validé |
| ObservationProcessing séparé | Validé |
| `queued / processing / processed / retrying / failed` | Validé |
| Plusieurs Signals possibles | Validé |
| Max 5 Signals générés | Validé |
| Observation reste brute et unique | Validé |
| Signals structurés multiples | Validé |
| Aggregation = Signal candidat agrégé, pas Observation entière | Validé |
| `no_signal_created` conservé | Validé |
| Pas de page détail Observation | Validé |
| Pas d'Observation brute dans Signal detail | Validé |
| Observation brute invisible UI produit | Validé |
| Checklist context optionnel | Validé |
| ObservationMedia belongs_to Observation | Validé |
| Max 3 photos | Validé |
| Temporary upload avant send | Validé |
| Cleanup orphan uploads | Validé |
| Audio supprimé après transcription | Validé |
| Draft local frontend uniquement | Validé |
| Operational Unit non demandée à l'utilisateur | Validé |
| Pas d'urgence déclarative | Validé |
| Pas d'anonyme | Validé |
| Retry automatique AI failure | Validé |
| Events Observation MVP | Validé |

---

# 23. Points à traiter dans d'autres domaines

## 23.1 Upload / Media Lifecycle

À cadrer ailleurs :
- formats exacts ;
- taille max ;
- compression ;
- stockage ;
- URL signées ;
- lifecycle media ;
- rétention ;
- suppression photos.

## 23.2 AI Pipeline Contract

À cadrer ailleurs :
- JSON strict ;
- schéma candidate signals ;
- confidence thresholds ;
- top 5 selection ;
- invalid output ;
- retry policy ;
- prompt context ;
- hallucinated domains.

## 23.3 Signal Domain

À cadrer ailleurs :
- modèle Signal complet ;
- lifecycle Signal ;
- aggregation ;
- split ;
- status ;
- urgency ;
- pinning ;
- resolved/canceled/archived.

## 23.4 Notification Matrix

À cadrer ailleurs :
- notification when Signal created ;
- when aggregated ;
- when failed ;
- when assigned ;
- push payload ;
- realtime broadcast.

## 23.5 Security / RGPD

À cadrer ailleurs :
- accès admin aux Observations brutes ;
- audit ;
- rétention ;
- données sensibles ;
- photos avec personnes ;
- droit suppression/export ;
- logs IA.

---

# 24. Recommandation finale

Le domaine Observation est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Observation = input brut invisible dans l'UI produit
Signal = unité opérationnelle visible
```

Le build doit maintenant s'appuyer sur :
- création Observation robuste ;
- processing async séparé ;
- media attachés à Observation ;
- pipeline IA qui produit 0 à 5 Signals ;
- table `ObservationSignalLink` pour tracer les créations/agrégations ;
- aucun écran détail Observation dans l'UI produit ;
- accès admin technique uniquement aux Observations brutes.

La prochaine étape logique est le **Signal Domain**, car il dépend directement des outcomes Observation.
