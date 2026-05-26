# PART 1 — SYSTEM FOUNDATIONS

## 1 — Product Vision

#### 1.1 — AI-Native Operational System

Houston est un système de coordination opérationnelle temps réel.

Le système transforme des remontées terrain brutes en situations opérationnelles structurées et supervisables.

*Houston ne repose pas sur :*

- des tickets
- des workflows figés
- des tâches isolées
- des conversations libres

*Houston repose sur :*

- des situations opérationnelles vivantes
- des événements métier runtime
- des Signals
- la coordination temps réel
- l’exécution terrain

**<u>Objectif principal :</u>**

*Réduire :*

- le bruit opérationnel
- les duplications
- les pertes de contexte
- les coordinations siloées
- la charge mentale terrain

*Tout en augmentant :*

- la visibilité opérationnelle
- la vitesse de réaction
- la coordination multi-domain
- la contextualisation runtime
- la supervision temps réel

**<u>Philosophie Runtime :</u>**

```txt
Input terrain brut
        ↓
Interprétation IA
        ↓
Structuration opérationnelle
        ↓
Signal partagé
        ↓
Coordination temps réel
        ↓
Actions
        ↓
Résolution
        ↓
Runtime enrichment
```

**<u>Ce que Houston N’EST PAS :</u>**

| Système        | Pourquoi                                         |
| -------------- | ------------------------------------------------ |
| Ticketing Tool | Les Signals représentent des situations vivantes |
| CRUD App       | Le runtime est event-driven                      |
| Chat App       | Le chat reste secondaire                         |
| IA autonome    | Le backend garde l’autorité                      |
| BPM figé       | Les situations évoluent dynamiquement            |

<u>**Ce que Houston EST :**</u>

| Type                      | Description                                                  |
| ------------------------- | ------------------------------------------------------------ |
| AI-Augmented              | L’IA structure les remontées terrain                         |
| Event-Driven              | Les événements pilotent le runtime                           |
| Signal-Oriented           | Les situations sont centrales                                |
| Realtime                  | Coordination continue                                        |
| Runtime-Enriched          | Le contexte s’enrichit progressivement                       |
| Operational Memory Driven | Le système construit une mémoire opérationnelle contextualisée |

#### 1.2 — AI-Assisted Operational Bootstrap

Houston vise un time-to-value opérationnel en quelques minutes.

*Le système démarre avec :*

- une configuration minimale
- une détection IA des activités
- une validation humaine légère
- un enrichissement runtime progressif

**<u>Bootstrap Runtime - Input onboarding :</u>**

```txt
Quelles sont les activites propres à votre établissement ?

"L'établissement contient un hôtel,
2 restaurants,
un rooftop,
des salles de séminaires,
un espace coworking
et une salle de sport."
```

**<u>Bootstrap Runtime - Le système génère automatiquement :</u>**

- Operational Modules
- Operational Domains
- Operational Units
- Runtime Semantic Vocabulary
- Runtime Tags
- Routing Hints
- structure opérationnelle initiale

**<u>Philosophie Time-To-Value :</u>**

```txt
Configuration minimale
        ↓
Bootstrap IA
        ↓
Validation humaine
        ↓
Activation immédiate
        ↓
Usage terrain réel
        ↓
Runtime enrichment progressif
```

#### 1.3 — Runtime Operational Enrichment

Le système devient plus pertinent à mesure que les opérations produisent du contexte runtime.

Le runtime enrichit progressivement :

- le vocabulaire métier
- les aliases sémantiques
- les routing hints
- les patterns opérationnels
- les comportements d’agrégation
- les runtime tags

**<u>Runtime Operational Memory :</u>**

Le système construit progressivement une mémoire opérationnelle contextualisée.

*Cette mémoire contient :*

- vocabulaire runtime
- patterns observés
- termes locaux
- routages fréquents
- corrections humaines
- aliases validés

**<u>Runtime Enrichment Philosophy :</u>**

*Le runtime enrichment :*

- n’est PAS du machine learning
- ne nécessite PAS de retraining
- ne modifie PAS le modèle IA
- n’est PAS autonome

*Le système utilise :*

```txt
LLM stateless
+
runtime semantic dictionaries
+
prompt enrichment
+
backend validation
```

**<u>Exemple Runtime Vocabulary :</u>**

```txt
"VRV"
→ HVAC / climatisation

"IRVE"
→ charging station

"coup de feu"
→ restaurant rush
```

**<u>Runtime Semantic Flow :</u>**

```txt
Observation
        ↓
Runtime semantic injection
        ↓
LLM interpretation
        ↓
Backend validation
        ↓
Signal structuring
```

**<u>Principe critique :</u>**

```txt
Le runtime enrichment n’est jamais du retraining IA.
```

#### 1.4 — Event-Driven Coordination

Le système fonctionne entièrement via des événements métier.

Chaque mutation importante produit un événement runtime.

*Les événements coordonnent :*

- les feeds
- les notifications
- les websockets
- les escalades
- les synchronisations
- les traitements IA
- les workers async

**<u>Global Event Flow :</u>**

```txt
Action utilisateur
        ↓
Validation backend
        ↓
Business Event
        ↓
Event Bus
        ↓
Async Consumers
        ├── AI Pipeline
        ├── Feed Updates
        ├── Notifications
        ├── Websocket Broadcast
        ├── Analytics
        └── Audit Logs
```

**<u>Exemple Runtime :</u>**

```txt
ObservationCreated
        ↓
ObservationQueuedForAI
        ↓
ObservationAnalyzed
        ↓
SignalCreated/SignalAggregated
        ↓
RealtimeBroadcast
        ↓
ManagersNotified
```

#### 1.5 — Backend-Controlled AI

*L’IA agit uniquement comme :*

- moteur d’interprétation
- moteur de structuration
- moteur de suggestion
- moteur d’enrichissement sémantique

Le backend reste l’autorité runtime unique.

**<u>AI Boundaries :</u>**

| Responsabilité           | IA   | Backend |
| ------------------------ | ---- | ------- |
| Compréhension sémantique | OUI  | NON     |
| Détection domains        | OUI  | VALIDE  |
| Runtime tags             | OUI  | VALIDE  |
| Permissions              | NON  | OUI     |
| Visibility               | NON  | OUI     |
| Lifecycle métier         | NON  | OUI     |
| Persistence              | NON  | OUI     |

**<u>Runtime Authority :</u>**

```txt
AI Output
        ↓
Backend Validation
        ↓
Business Rules
        ↓
Permissions
        ↓
Persistence
        ↓
Realtime Broadcast
```

## 2 — Global Architecture Overview

#### 2.1 — AI-Native Event-Driven Architecture

```txt
                        ┌────────────────────┐
                        │ Mobile Clients     │
                        └─────────┬──────────┘
                                  │
                        ┌─────────▼──────────┐
                        │ API Gateway        │
                        │ Auth + Validation  │
                        └─────────┬──────────┘
                                  │
                ┌─────────────────┼──────────────────┐
                │                 │                  │
      ┌─────────▼──────┐ ┌────────▼────────┐ ┌──────▼─────────┐
      │ Observation    │ │ Signal System   │ │ Action System  │
      │ System         │ │                  │ │                │
      └─────────┬──────┘ └────────┬────────┘ └──────┬─────────┘
                │                 │                  │
                └─────────────────┼──────────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │ Event Bus          │
                        └─────────┬──────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐      ┌─────────▼────────┐      ┌────────▼────────┐
│ AI Pipeline    │      │ Notification     │      │ Realtime Engine │
│ Async Workers  │      │ System           │      │ Websocket Hub   │
└───────┬────────┘      └─────────┬────────┘      └────────┬────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │ PostgreSQL         │
                        │ Canonical State    │
                        └────────────────────┘
```

#### 2.2 — System Boundaries

| Système                | Responsabilité              |
| ---------------------- | --------------------------- |
| API Layer              | Validation & orchestration  |
| AI Pipeline            | Structuration sémantique    |
| Event Bus              | Coordination async          |
| Realtime Engine        | Synchronisation temps réel  |
| PostgreSQL             | Source canonique            |
| Notification System    | Coordination opérationnelle |
| Runtime Semantic Layer | Enrichissement contextuel   |

#### 2.3 — Runtime Operational Loop

```txt
Input terrain
        ↓
Observation
        ↓
AI Structuring
        ↓
Signal
        ↓
Realtime Coordination
        ↓
Actions
        ↓
Resolution
        ↓
Runtime Enrichment
```

#### 2.4 — Async Principles

| Principe              | Description             |
| --------------------- | ----------------------- |
| Persistence immédiate | Jamais bloquer sur l’IA |
| IA async              | Queue-based             |
| Event-driven realtime | Pas de polling massif   |
| Backend déterministe  | Output IA validé        |
| Broadcast filtré      | Respect visibilité      |

**<u>Observation Async Flow :</u>**

```txt
Observation submitted
        ↓
Immediate persistence
        ↓
Instant UI feedback
        ↓
AI Queue
        ↓
AI Structuring
        ↓
Backend Validation
        ↓
Signal Creation
        ↓
Realtime Feed Insertion
```

## 3 — Core Operational Concepts

#### 3.1 — Operational Modules

Les Operational Modules représentent les activités présentes dans un établissement.

Un établissement peut contenir plusieurs modules simultanément.

**<u>Exemple — Mama Shelter :</u>**

```txt
Mama Shelter
├── Hotel
├── Restaurant
├── Rooftop
├── Seminar Rooms
└── Coworking
```

**<u>Exemple — Shopping Mall :</u>**

```txt
Shopping Mall
├── Retail
├── Food Court
├── Parking
└── Entertainment
```

**<u>Module Bootstrap :</u>**

*Chaque module injecte :*

- Operational Domains
- Operational Units
- Runtime Semantic Vocabulary
- Runtime Tags
- Routing Hints
- exemples opérationnels

**<u>Module Flow :</u>**

```txt
Operational Module
        ↓
Operational Bootstrap
        ↓
Context Injection
        ↓
Minimal Operational Structure
        ↓
Runtime Enrichment
```

#### 3.2 — Operational Domains

Les Operational Domains représentent des scopes de coordination opérationnelle.

*Ils structurent :*

- la visibilité
- la supervision
- les notifications
- les realtime feeds
- la coordination multi-équipes

**<u>Exemples :</u>**

```txt
Maintenance
Security
Housekeeping
Guest Experience
Pricing
Communication
```

**<u>Distinction critique :</u>**

```txt
Operational Module = activité établissement

Operational Domain = coordination opérationnelle
```

#### 3.3 — Runtime Semantic Vocabulary

Le Runtime Semantic Vocabulary représente le langage réel utilisé sur le terrain.

*Le système utilise ce vocabulaire pour :*

- améliorer l’interprétation IA
- contextualiser les Signals
- enrichir les prompts
- améliorer le routage
- améliorer l’agrégation

**<u>Exemple :</u>**

| Runtime Vocabulary | Interprétation        |
| ------------------ | --------------------- |
| "VRV"              | climatisation / HVAC  |
| "IRVE"             | charging station      |
| "coup de feu"      | restaurant rush       |
| "PC sécurité"      | security control room |

**<u>Semantic Runtime Flow :</u>**

```txt
Runtime Vocabulary
        ↓
Prompt Enrichment
        ↓
LLM Interpretation
        ↓
Runtime Tags
        ↓
Backend Validation
```

**<u>Principe critique :</u>**

```txt
Le runtime semantic vocabulary
n’est PAS une taxonomie métier.
```

#### 3.4 — Runtime Tags

Les Runtime Tags représentent des labels contextuels flexibles.

*Ils servent à :*

- enrichir les Signals
- améliorer la recherche
- améliorer l’agrégation
- améliorer les analytics
- améliorer le routage

**<u>Exemple</u>**

```txt
Observation
        ↓
"La borne Tesla du parking B2 ne démarre plus."

Runtime Tags
        ↓
[
  "charging_station",
  "parking",
  "equipment_failure"
]
```

**<u>Principe critique :</u>**

```txt
Les runtime tags ne pilotent jamais les permissions.
```

#### 3.5 — Operational Units

Les Operational Units représentent des zones physiques ou logiques.

*Elles servent à :*

- contextualiser les situations
- améliorer l’agrégation
- améliorer la supervision
- améliorer la compréhension IA

**<u>Exemples :</u>**

```txt
Lobby
Room 312
Parking B2
Rooftop Kitchen
Seminar Room A
North Entrance
Food Court
```

#### 3.6 — Checklists

Les Checklists représentent des routines opérationnelles structurées et réutilisables.

Elles servent à :

- standardiser les opérations terrain
- guider les inspections
- réduire les oublis
- produire des Observations contextualisées
- structurer le travail récurrent

**<u>Types de Checklists :</u>**

| Type               | Description |
| ------------------ | ----------- |
| Shared Checklist   | Public      |
| Personal Checklist | Privé       |

**<u>Shared Checklist :</u>**

```
PHYLOSOPHIE

Shared Checklist = une routine opérationnelle appartenant à l’établissement

Elle est :
- créée par un manager/directeur
- réutilisable
- standardisée
- assignable
- établissement-scoped

SHARED CHECKLIST STRUCTURE 

Shared Checklist
├── title
├── description
├── checklist_tasks[]
├── operational_domains[]
├── operational_units[]
├── establishment_id
├── created_by
├── assigned_to
├── status
└── timestamps

SHARED CHECKLIST MODEL

1 active checklist = 1 assignee maximum

SHARED CHECKLIST RUNTIME FLOW

Manager creates checklist
        ↓
Checklist stored in Checklist Module
        ↓
Checklist assigned to one user
        ↓
Checklist appears in Action Feed
        ↓
Execution runtime
        ↓
Checklist completed

ATTENTION

Checklist
≠
Action

SHARED CHECKLIST LIFECYCLE

DRAFT
    ↓
ACTIVE
    ↓
ASSIGNED
    ↓
IN_PROGRESS
    ↓
COMPLETED
    ↓
ARCHIVED

SHARED CHECKLIST LIFECYCLE DESCRIPTION

| State       | Description                         |
| ----------- | ----------------------------------- |
| draft       | Checklist non publiée               |
| active      | Disponible dans le Checklist Module |
| assigned    | Assignée à un utilisateur           |
| in_progress | Exécution runtime en cours          |
| completed   | Toutes tâches traitées              |
| archived    | Historisée                          |
| canceled    | Annulée                             |

CHECKLISTTASK STRUCTURE

Checklist Task
├── instructions
├── checklist_id
├── operationals_domains[]
├── requires_observation
├── order
└── status

CHECKLISTTASK LIFECYCLE

pending
    ↓
done

OR

pending
    ↓
skipped

COMPLETION RULES

Checklist COMPLETED = all tasks are:
- done
OR
- skipped
```

**<u>Personal checklist :</u>**

```
PHILOSOPHY

une routine privée réutilisable uniquement par son créateur
Une Personal Checklist appartient uniquement à son créateur.

Elle sert :
- d’organisation personnelle
- de mémo terrain
- de routine individuelle

PERSONAL CHECKLIST STRUCTURE

Personal Checklist
├── title
├── checklist_tasks[]
├── operational_domains[]
├── operational_units[]
├── created_by
├── private
├── status
└── timestamps

PERSONAL CHECKLIST LIFECYCLE

DRAFT
    ↓
ACTIVE
    ↓
IN_PROGRESS
    ↓
COMPLETED
    ↓
ARCHIVED

SHARED CHECKLIST LIFECYCLE DESCRIPTION

| State       | Description                         |
| ----------- | ----------------------------------- |
| draft       | Checklist non publiée               |
| active      | Disponible dans le Checklist Module |
| in_progress | Exécution runtime en cours          |
| completed   | Toutes tâches traitées              |
| archived    | Historisée                          |
| canceled    | Annulée                             |

PERSONAL CHECKLIST RUNTIME FLOW

User creates checklist
        ↓
Checklist visible only to created_by
        ↓
Reusable only by created_by
        ↓
Execution
        ↓
Checklist completed

PERSONAL CHECKLIST VISIBILITY

Les Personal Checklists :
- n’apparaissent PAS dans le Checklist Module global
- ne sont PAS partageables
- ne sont PAS assignables
- restent privées

CHECKLISTTASK LIFECYCLE

pending
    ↓
done

OR

pending
    ↓
skipped

COMPLETION RULES

Checklist COMPLETED = all tasks are:
- done
OR
- skipped
```

**<u>Checklist module :</u>**

Le Checklist Module centralise les Shared Checklist et les Personal Checklist

*Ce sont les :*

- rôles
- permissions runtime
- règles de visibilité

*qui déterminent ce que le user voit réellement.*

```
VISIBILITY MATRIX 

| Role     | Shared Checklists | Personal Checklists |
| -------- | ----------------- | ------------------- |
| Owner    | YES               | Own only            |
| Director | YES               | Own only            |
| Manager  | YES               | Own only            |
| Staff    | NO                | Own only            |

Très important.
Le Staff :
- ne voit PAS les Shared Checklists globales
- ne browse PAS les routines établissement
- n’administre PAS les templates opérationnels
- Le fait qu’un Staff ne voie pas les Shared Checklists ne l’empêche PAS d’exécuter une Shared Checklist assignée
- Checklist Module visibility ≠ Execution visibility

VISIBILITY RESOLUTION

User
        ↓
Role Resolution
        ↓
Checklist Visibility Rules
        ↓
Visible Checklists

CHECKLIST MODULE RUNTIME FLOW

Checklist Module
├── Shared Checklists
├── Personal Checklists
│
└── Visibility Resolution
         ↓
Role-Based Filtering
         ↓
Visible Checklists
         ↓
Assignment Runtime
         ↓
Action Feed
```

**<u>Exemple :</u>**

```
Shared Checklist "Ouverture Restaurant"

├── Vérifier chambre froide
├── Vérifier extraction cuisine
├── Vérifier propreté salle
├── Vérifier terminal paiement
└── Vérifier stock boissons
```

**<u>Contextualized Observation Flow :</u>**

Une Checklist peut produire des Observations contextualisées.

```
RUNTIME FLOW

Checklist Task
        ↓
User reports anomaly
        ↓
Observation enriched with:
- checklist context
- task context
- operational unit
        ↓
AI Structuring Pipeline
        ↓
Potential Signal
```

**<u>Checklist Principles :</u>**

```
- Checklist Module centralizes all checklists
- Roles drive checklist visibility
- Shared Checklists belong to establishments
- Personal Checklists belong to users
- Staff users cannot browse Shared Checklists
- Assigned Shared Checklists appear in Action Feed
- Checklist visibility remains backend-resolved
- Execution visibility differs from module visibility
```

#### 3.7 — Observations

Les Observations représentent des remontées terrain brutes immuables.

*Une Observation peut provenir :*

- du texte
- d’une transcription audio
- d’une checklist

**<u>Observation Philosophy :</u>**

```txt
Observation = Raw Field Input
```

**<u>Observation Lifecycle :</u>**

```txt
Draft
    ↓
Created
    ↓
Persisted
    ↓
AI Queue
    ↓
AI Processing
    ↓
Signal Created / Aggregated
```

#### 3.8 — Signals

Les Signals représentent des situations opérationnelles partagées et vivantes.

*Le Signal centralise progressivement :*

- Observations
- commentaires
- Actions
- événements runtime
- priorité
- historique opérationnel

**<u>Signal Philosophy :</u>**

```txt
Signal = Shared Operational Situation
```

**<u>Signal Structure :</u>**

```txt
Signal
├── title
├── description
├── detected_domains[]
├── visibility_domains[]
├── active_domains[]
├── runtime_tags[]
├── urgency
├── pinned
├── status
├── observations_count
├── created_from
└── timestamps
```

**<u>Structure component :</u>**

| Champ              | Description                    |
| ------------------ | ------------------------------ |
| title              | Résumé opérationnel court      |
| description        | Situation contextualisée       |
| detected_domains[] | Domains détectés par IA        |
| active_domains[]   | Domains actuellement impliqués |
| runtime_tags[]     | Labels runtime contextuels     |
| urgency            | Niveau de priorité             |
| pinned             | Visibilité forcée              |
| status             | État runtime du Signal         |
| signal_count       | Nombre de Signal agrégées      |
| created_from       | Observation source initiale    |

**<u>Signal Lifecycle :</u>**

```
┌────────────────────┐
│        OPEN        │
│                    │
│ Situation active   │
│ Aucun plan d’action│
└─────────┬──────────┘
          │
          │ Manager crée une Action
          ▼
┌────────────────────┐
│    IN_PROGRESS     │
│                    │
│ Situation prise    │
│ en charge          │
└─────────┬──────────┘
          │
          │ Toutes les Actions
          │ validées / canceled
          ▼
┌────────────────────┐
│      RESOLVED      │
│                    │
│ Situation résolue  │
│ opérationnellement │
└─────────┬──────────┘
          │
          │ Retention policy
          │ ou archivage manuel
          ▼
┌────────────────────┐
│      ARCHIVED      │
│                    │
│ Signal historisé   │
└────────────────────┘

Alternative state :
┌────────────────────┐
│      Canceled      │
│                    │
│ Signal annulé		   │
└────────────────────┘

```

**<u>Lifecycle description :</u>**

| Status      | Qui agit         | Action utilisateur             |
| ----------- | ---------------- | ------------------------------ |
| open        | Manager          | Créer Action / pin / escalader |
| in_progress | Managers & Teams | Coordonner / commenter / agir  |
| resolved    | System / Manager | Validation résolution          |
| archived    | System / Manager | Archivage                      |
| canceled    | Manager          | Annuler situation              |

**<u>Signal Coordination :</u>**

Un Signal n’a PAS de propriétaire fort.

*Plusieurs managers peuvent :*

- coordonner
- commenter
- superviser
- créer des Actions
- intervenir

**<u>Signal Feed - Runtime Ordering :</u>**

```txt
Pinned Signals
        ↓
Urgent Signals
        ↓
Open Signals
        ↓
In Progress Signals
        ↓
Resolved Signals
```

**<u>Signal Runtime Flow :</u>**

```txt
Observation
        ↓
Signal Created
        ↓
New Observations
        ↓
Signal Aggregation
        ↓
Realtime Coordination (Feed Signals)
        ↓
Actions
        ↓
Resolution
```

**<u>Pinned Signals :</u>**

Le pinning permet de maintenir une visibilité élevée sans nécessairement créer d’Action

*Le pinning sert à :*

- maintenir une visibilité élevée
- partager une information importante
- superviser une situation persistante

```
Exemples :

- vigilance météo
- travaux temporaires
- humidité persistante
- ascenseur fragile
- planning disponible

Pinning Runtime Behavior :

Manager pins Signal
        ↓
Signal moved to top
        ↓
Realtime Feed Update
        ↓
Visibility maintained
```

**<u>Signal Visibility Resolution :</u>**

```
Signal Created
        ↓
Backend Visibility Resolution
        ↓
Authorized Users
        ↓
Realtime Broadcast
        ↓
Feed Insertion
```

**<u>Signal Runtime Coordination :</u>**

*Un Signal peut provoquer :*

- notifications
- realtime updates
- feed reordering
- escalades
- Action creation
- Pinned
- cross-domain coordination
- runtime enrichment

**<u>Signal Architecture Principles :</u>**

```
- Signals represent operational situations
- Signals remain shared objects
- Signals are realtime coordination objects
- Signals are not tasks
- Pinning ≠ status
- Aggregation reduces operational noise
- Visibility is backend-resolved
- Signals remain supervision-oriented
```

#### 3.9 — Actions

Les Actions représentent l’exécution opérationnelle avec responsabilité engagée.

Une Action existe lorsqu’une intervention concrète devient nécessaire.

**<u>Action Philosophy :</u>**

```txt
Action = Operational Accountability
```

**<u>Action Structure :</u>**

```
Action
├── title
├── description
├── signal_id
├── operational_domain
├── created_by
├── assigned_to
├── priority
├── status
├── due_at
├── validation_required
├── validated_by
└── timestamps
```

**<u>Description des composants :</u>** 

| Champ               | Description                   |
| ------------------- | ----------------------------- |
| title               | Résumé court de l'action      |
| description         | Contexte et travail attendu   |
| signal_id           | Signal source lié             |
| operational_domain  | Domaine responsable           |
| created_by          | Auteur de l’Action            |
| assigned_to         | Responsable opérationnel      |
| priority            | Priorité d’exécution          |
| status              | État runtime de l’Action      |
| due_at              | Échéance éventuelle           |
| validation_required | Validation manager nécessaire |
| validated_by        | Manager ayant validé          |

**<u>Action Lifecycle :</u>**

```
		 		SIGNAL
          │
          │ Manager Creat & Assign Action
          ▼
┌────────────────────┐
│       OPENED       │
│                    │
│ Action créée       │
│ Non assignée			 |
│ Responsable défini |
| Notification envoyée
└─────────┬──────────┘
          │													
          │ Assignee accepte				
          ▼													
┌────────────────────┐							
│      IN_PROGRESS   │							
│                    │							
│ Intervention       │--------------|				
│ prise en charge		 |							|	
│ en cours					 |							|
└─────────┬──────────┘							|
          │													|		
          │ Assignee mark as done		|
          ▼													|
┌────────────────────┐							|
│ PENDING_VALIDATION │							|	
│                    │							|
│ Validation manager │							|
│ requise            │							|
└──────┬───────┬─────┘							|
       │       │										|
       │       │ Manager reopen			| Reprise travail/Assignee accepte
       │       ▼										|	
       │  ┌──────────────────┐			|
       │  │    REOPENED      │			|
       │  │                  │------|
       │  │ Action réouverte │
       │  └─────────-────────┘   										       
			 |	
			 |	Manager valide
       ▼
┌────────────────────┐
│        DONE        │
│                    │
│ Intervention       │
│ validée            │	
└────────────────────┘

Alternative state :
┌────────────────────┐
│      CANCELED      │
│                    │
│ Action        		 │
│ Annulée            │
└────────────────────┘
```

**<u>Lifecycle description :</u>**

| Status             | Qui agit       | Action utilisateur                  |
| ------------------ | -------------- | ----------------------------------- |
| opened             | Manager        | Créer et Assigner l’Action          |
| opened             | Assignee       | Accepter                            |
| in_progress        | Assignee       | Ajouter commentaires / Mark as done |
| pending_validation | Manager        | Valider / Reopen                    |
| reopened           | Assignee       | Reprendre intervention / Accepter   |
| done               | Manager/System | Clôture finale                      |
| canceled           | Manager        | Annuler intervention                |

**<u>Action runtime workflow :</u>**

```
Signal
    ↓
Manager identifies required intervention
    ↓
Action created and assigned
    ↓
Realtime Notification
    ↓
Execution
    ↓
Validation
```

**<u>Runtime Coordination :</u>**

*Une Action peut :*

- générer des événements runtime
- notifier des utilisateurs
- déclencher des escalades
- modifier le statut du Signal
- enrichir le contexte opérationnel

**<u>Action validation workflow :</u>**

```
User marks action completed
        ↓
Action enters status pending_validation
        ↓
Manager reviews execution
        ↓
Validation OR Rejection
        ↓
Action enters status done OR reopened
```

**<u>Escalation :</u>**

| Condition          | Escalation                                          |
| ------------------ | --------------------------------------------------- |
| No acceptance > 1h | Notify managers                                     |
| SLA breach         | Immediate escalation ; Notify managers ; Feed boost |

```
Action Created & Assigned
        ↓
OPENED
        ↓
Timer SLA starts
        ↓
No acceptance after 1h
        ↓
Escalation Triggered
        ↓
Escalation Event Created
        ↓
Realtime Notifications
        ↓
Managers alerted
        ↓
Priority upgraded
        ↓
Action visibility increased
```

```
┌────────────────────┐
│  ACTION	OPENED     │
│                    │
│ Waiting acceptance │
└─────────┬──────────┘
          │
          │ > 1h without acceptance
          ▼
┌────────────────────┐
│     ESCALATION     │
│                    │
│ SLA breached       │
│ No ownership taken │
└─────────┬──────────┘
          │
          ├─────────────────────┐
          │                     │
          ▼                     ▼
┌──────────────────┐   ┌──────────────────┐
│ Notify Managers  │   │ Increase Priority│
└──────────────────┘   └──────────────────┘
          │                     │
          └──────────┬──────────┘
                     ▼
          ┌────────────────────┐
          │ Action Feed Update │
          │ Realtime Broadcast │
          └────────────────────┘
```

**<u>Architecture principles</u>**

```
- Actions create accountability
- Signals remain shared situations
- Actions remain executable objects
- Assignment controls responsibility
- Validation controls operational quality
- Action Feed remains execution-focused
```

#### 3.10 — Signal Feed vs Action Feed

*Houston sépare volontairement :*

- supervision opérationnelle
- exécution opérationnelle

**<u>Signal Feed :</u>**

*Le Signal Feed sert à :*

- superviser les Signals
- suivre les escalades
- maintenir la visibilité opérationnelle
- coordonner les domains

**<u>Action Feed :</u>**

*Le Action Feed sert à :*

- exécuter les interventions
- suivre les responsabilités
- gérer les validations
- superviser la charge opérationnelle

**<u>Distinction critique :</u>**

```txt
Signal Feed = supervision temps réel

Action Feed = exécution opérationnelle
```

#### 3.11 — General Chat

Le General Chat est un espace de communication libre.

*Le chat permet :*

- échanges rapides
- questions
- coordination informelle
- communication équipe

**<u>Chat Philosophy :</u>**

```txt
General Chat = Free-Form Communication
```

**<u>Frontière critique :</u>**

*Le Chat n’alimente jamais :*

- le pipeline IA
- les Signals
- les Actions
- le runtime enrichment

**<u>Exemple :</u>**

```txt
Chat =
"Qui peut remplacer Julien ce soir ?"

Signal =
"Fuite eau devant chambre 312"
```

#### 3.12 — Visibility Resolution Principles

La visibilité runtime est entièrement backend-resolved.

La visibilité dépend :

- rôle utilisateur
- établissement actif
- Operational Domains
- runtime rules
- realtime filtering

**<u>Realtime Filtering :</u>**

```txt
Business Event
        ↓
Visibility Resolution
        ↓
Authorized Users
        ↓
Realtime Broadcast
```

**<u>Principe critique :</u>**

```txt
La visibilité runtime est toujours backend-resolved.
```

#### 3.13 — Core Concepts Summary

| Objet        | Rôle                      |
| ------------ | ------------------------- |
| Checklist    | Structurer les routines   |
| Observation  | Capturer le terrain       |
| Signal       | Structurer les situations |
| Action       | Structurer l’exécution    |
| General Chat | Communication libre       |

**<u>Runtime Semantic Hierarchy :</u>**

| Concept            | Rôle                        |
| ------------------ | --------------------------- |
| Module             | Type d’activité             |
| Domain             | Coordination opérationnelle |
| Unit               | Zone physique/logique       |
| Runtime Tag        | Label contextuel flexible   |
| Runtime Vocabulary | Langage terrain             |
| Semantic Alias     | Synonyme runtime            |
| Routing Hint       | Aide au routage IA          |

# PART 2 — ORGANIZATION MODEL

## 1 — Runtime Organization Topology

#### 1.1 — Runtime Partitioning

Houston partitionne le runtime par établissement.

*Chaque établissement possède :*

- ses Checklist
- ses Signals
- ses Actions
- ses realtime feeds
- son operational context (module, domain, unit)
- son runtime vocabulary
- ses runtime tags
- ses routing behaviors
- son operational memory

**<u>Runtime Architecture :</u>**

```txt
Organization
├── Establishment Runtime A
│    ├── Checklist
│    ├── Signals
│    ├── Actions
│    ├── Operational Context
│    ├── Runtime Vocabulary
│    ├── Runtime Tags
│    └── Operational Memory
│
├── Establishment Runtime B
│    ├── Checklist
│    ├── Signals
│    ├── Actions
│    ├── Operational Context
│    ├── Runtime Vocabulary
│    ├── Runtime Tags
│    └── Operational Memory
│
└── Establishment Runtime C
		 ├── Checklist
     ├── Signals
     ├── Actions
     ├── Operational Context
     ├── Runtime Vocabulary
     ├── Runtime Tags
     └── Operational Memory
```

**<u>Principe critique :</u>**

```txt
Le runtime opérationnel reste toujours établissement-scoped.
```

#### 1.2 — Runtime Context

Chaque établissement construit progressivement son propre contexte opérationnel.

**<u>Runtime Context Structure :</u>**

```txt
Establishment Runtime Context
├── Checklist
├── Active Signals
├── Active Actions
├── Runtime Vocabulary
├── Runtime Tags
├── Runtime Patterns
├── Routing Behaviors
├── Operational Memory
└── Realtime Visibility Context
```

**<u>Exemple :</u>**

```txt
Mama Shelter Paris

"la 312"
→ room reference

"la plonge"
→ restaurant kitchen area

"roof"
→ rooftop operational unit
```

#### 1.3 — Runtime Isolation Principles

Les enrichissements runtime restent toujours scoped à leur établissement.

**<u>Isolation Rules :</u>**

| Élément              | Scope         |
| -------------------- | ------------- |
| Runtime vocabulary   | établissement |
| Runtime tags         | établissement |
| Routing corrections  | établissement |
| Aggregation behavior | établissement |
| Operational memory   | établissement |

**<u>Principe critique :</u>**

```txt
Le runtime d’un établissement
ne doit jamais contaminer
celui d’un autre.
```

## 2 — Runtime Identity & Visibility Model

#### 2.1 — User Model

Un utilisateur peut appartenir à plusieurs établissements.

*Mais :*

- un seul établissement reste actif à la fois
- le runtime reste contextualisé

**<u>User Structure</u>**

```txt
User
├── first_name
├── last_name
├── email
├── Phone
├── role
├── establishments[]
├── operational_domains[]
├── active_user
└── active_establishment
```

**<u>Runtime Context Resolution :</u>**

```txt
User
        ↓
Active Establishment
        ↓
Operational Domains
        ↓
Visibility Scope
        ↓
Realtime Feeds
```

#### 2.2 — Visibility Model

*La visibilité runtime dépend :*

- du rôle
- de l’établissement actif
- des domains
- des runtime rules
- du backend filtering

**<u>Visibility Resolution :</u>**

```txt
User
        ↓
Role
        ↓
Active Establishment
        ↓
Operational Domains
        ↓
Runtime Rules
        ↓
Visible Signals & Actions
```

**<u>Principe critique :</u>**

```txt
Role ≠ Visibility
```

#### 2.3 — Multi-Domain Coordination

Une situation peut concerner plusieurs domains simultanément.

**<u>Exemple :</u>**

```txt
Water Leak
├── Maintenance
├── Security
└── Hygiene
```

**<u>Effets runtime :</u>**

Tous les domains concernés peuvent :

- voir le Signal
- commenter
- coordonner
- créer des Actions
- superviser

**<u>Principe critique :</u>**

```txt
Un Signal peut être multi-domain
sans ownership fort.
```

#### 2.4 — Runtime Presence

Le système maintient un contexte de présence runtime.

**<u>Runtime Presence Context :</u>**

```txt
User
        ↓
Active Session
        ↓
Active Establishment
        ↓
Operational Scope
        ↓
Realtime Subscription
```

## 3 — Governance & RBAC

#### 3.1 — Governance Scopes

| Scope              | Responsibility              |
| ------------------ | --------------------------- |
| Organization       | Gouvernance globale         |
| Establishment      | Supervision opérationnelle  |
| Operational Domain | Coordination opérationnelle |
| Action             | Accountability exécution    |

**<u>Governance Flow :</u>**

```txt
Organization
        ↓
Establishment Supervision
        ↓
Operational Coordination
        ↓
Execution Accountability
```

#### 3.2 — Role Hierarchy

```txt
OWNER
    ↓
DIRECTOR
    ↓
MANAGER
    ↓
STAFF
```

**<u>Role Responsibilities :</u>**

| Role     | Responsibilities              |
| -------- | ----------------------------- |
| Owner    | Gouvernance organization-wide |
| Director | Supervision établissement     |
| Manager  | Coordination opérationnelle   |
| Staff    | Participation terrain         |

#### 3.3 — RBAC Architecture

*Le système sépare volontairement :*

- rôle
- visibilité
- coordination runtime

**<u>Authorization Resolution :</u>**

```txt
Role
        ↓
Permissions
        ↓
Operational Domains
        ↓
Runtime Visibility
```

**<u>Principes critiques :</u>**

```txt
Le frontend
ne résout jamais
les permissions runtime.
Le websocket
ne bypass jamais
les règles backend.
```

#### 3.4 — Invitation Workflow

```txt
Owner
    ↓
Invite Director
    ↓
Invite Manager
    ↓
Invite Staff
```

**<u>Runtime Activation Flow :</u>**

```txt
Invitation
        ↓
Role Assignment
        ↓
Establishment Assignment
        ↓
Operational Domains Assignment
        ↓
Visibility Activation
        ↓
Realtime Subscription
```

#### 3.5 — Runtime Authorization Principles

| Principe                         | Description                   |
| -------------------------------- | ----------------------------- |
| Roles ≠ Visibility               | Le rôle seul ne suffit jamais |
| Backend-resolved visibility      | Jamais frontend               |
| Runtime filtering obligatoire    | Tous les événements           |
| Domains pilotent la coordination | Pas les rôles                 |
| Signals restent partagés         | Pas de strong ownership       |
| Realtime filtering systématique  | Aucun bypass websocket        |

# PART 3 — ONBOARDING SYSTEM

## 1 — Progressive Onboarding Philosophy

#### 1.1 — Fast Time-To-Value

Houston privilégie une activation opérationnelle immédiate.

*Le système évite :*

- les configurations longues
- les taxonomies complexes
- les setups administratifs lourds
- les workflows de paramétrage exhaustifs

*L’objectif :*

- permettre une utilisation terrain en quelques minutes
- produire rapidement les premiers Signals
- démarrer la coordination opérationnelle immédiatement

**<u>Philosophie Runtime :</u>**

```text
Configuration minimale
        ↓
Bootstrap IA
        ↓
Validation humaine légère
        ↓
Activation runtime
        ↓
Première utilisation terrain
```

**<u>Principe critique :</u>**

```text
L’onboarding initialise
le runtime opérationnel.

Il ne cherche pas
à modéliser parfaitement
l’organisation dès le départ.
```

#### 1.2 — Minimal Initial Configuration

Le système demande uniquement les informations nécessaires au bootstrap opérationnel initial.

**<u>Informations minimales requises :</u>**

| Élément                            | Objectif                |
| ---------------------------------- | ----------------------- |
| Organization Name                  | contexte global         |
| Establishment Name                 | contexte runtime        |
| Establishment Activity Description | interprétation IA       |
| Operational Modules                | bootstrap métier        |
| Managers initiaux                  | activation coordination |

**<u>Principe critique :</u>**

```text
Le runtime réel enrichit progressivement
la structure opérationnelle.
```

#### 1.3 — Human-Validated AI

*L’IA propose :*

- des modules
- des domains
- des runtime tags
- des operational units
- des comportements de routage

Mais aucune structure runtime n’est activée automatiquement sans validation humaine.

**<u>Architecture Validation :</u>**

```text
AI Interpretation
        ↓
Runtime Proposal
        ↓
Human Validation
        ↓
Runtime Activation
```

**<u>Principe critique :</u>**

```text
Le système suggère, les humains valident.
```

#### 1.4 — Runtime Learning Transition

L’onboarding initialise uniquement le contexte runtime minimal.

Le véritable enrichissement opérationnel commence avec :

- les premières Observations
- les premiers Signals
- les premiers routages
- les premières corrections humaines

**<u>Transition Runtime :</u>**

```text
Initial Bootstrap
        ↓
First Observations
        ↓
Runtime Learning
        ↓
Operational Enrichment
```

## 2 — Operational Context Interpretation

#### 2.1 — Free-Text Establishment Description

Le système utilise une description libre de l’établissement comme point d’entrée principal du bootstrap IA.

**<u>Exemple :</u>**

```text
Décrivez les activités de votre établissement :

“Nous sommes un hôtel avec :
- rooftop
- restaurant
- coworking
- salles de séminaire”
```

**<u>Données interprétées :</u>**

*Le système peut extraire :*

- des Operational Modules
- des Operational Domains
- des Operational Units
- du vocabulaire métier
- des patterns opérationnels
- des suggestions de domains

#### 2.2 — AI Operational Interpretation

Le moteur IA interprète le contexte opérationnel fourni.

*Le système génère :*

- des hypothèses runtime
- des suggestions structurelles
- des runtime tags
- des patterns métier potentiels
- des comportements de routage initiaux

**<u>Pipeline interprétation :</u>**

```text
Free-text Description
        ↓
Semantic Interpretation
        ↓
Operational Extraction
        ↓
Runtime Proposals
```

**<u>Exemple :</u>**

```text
Input :
“Restaurant rooftop avec bar et cuisine”

Output AI
{
  "modules": [
    "restaurant",
    "rooftop"
  ],
  "domains": [
    "maintenance",
    "hygiene",
    "guest_experience"
  ],
  "runtime_tags": [
    "kitchen",
    "bar",
    "food_service"
  ]
}
```

#### 2.3 — Human Validation Layer

Toutes les suggestions IA restent validables avant activation runtime.

*Les utilisateurs peuvent :*

- accepter
- modifier
- supprimer
- compléter

*les structures proposées.*

**<u>Validation Runtime :</u>**

```text
AI Proposal
        ↓
Human Review
        ↓
Runtime Validation
        ↓
Activation
```

#### 2.4 — Modules Activation

Les Operational Modules validés activent automatiquement :

- des domains initiaux
- du vocabulaire métier
- des runtime tags
- des unités opérationnelles
- des comportements de routage initiaux

**<u>Activation Runtime :</u>**

```text
Operational Module
        ↓
Runtime Bootstrap
        ↓
Operational Context
        ↓
Initial Runtime Activation
```

#### 2.5 — Operational Confidence Resolution

Le système associe un niveau de confiance aux interprétations IA.

Les éléments à faible confiance nécessitent :

- validation humaine
- correction
- suppression éventuelle

**<u>Exemple :</u>**

```text
Input :
“Rooftop avec cuisine”

Confidence :
- rooftop module → 96%
- restaurant module → 82%
- event module → 41%
```

**<u>Principe critique :</u>**

```text
La confiance IA
n’est jamais suffisante
pour bypass la validation humaine.
```

## 4 — Operational Bootstrap Engine

#### 4.1 — Domains Injection

Les modules activés injectent des Operational Domains initiaux.

*Ces domains servent immédiatement à :*

- structurer les coordinations
- filtrer les feeds
- initialiser le routage runtime

**<u>Exemple :</u>**

```text
Restaurant Module
        ↓
Domains
├── Hygiene
├── Maintenance
├── Food Service
└── Guest Experience
```

#### 4.2 — Runtime Tags Bootstrap

Le système initialise des runtime tags cohérents avec les modules activés.

*Les runtime tags servent à :*

- structurer les situations
- améliorer le routage
- améliorer l’agrégation
- améliorer le contexte opérationnel

**<u>Principe critique :</u>**

```text
Les Runtime Tags
ne représentent pas
une taxonomie métier stricte.
```

**<u>Exemple :</u>**

```json
[
  "kitchen",
  "food_service",
  "bar",
  "cleaning",
  "equipment"
]
```

#### 4.3 — Semantic Vocabulary Bootstrap

Le système initialise un vocabulaire opérationnel de départ.

Ce vocabulaire est ensuite enrichi progressivement par le runtime réel.

**<u>Sources initiales :</u>**

| Source                    | Usage                     |
| ------------------------- | ------------------------- |
| Operational Modules       | vocabulaire métier        |
| Establishment Description | vocabulaire local         |
| Runtime Usage             | enrichissement progressif |

**<u>Exemple :</u>**

```text
“rooftop”
“la plonge”
“back office”
“food court”
“réserve”
```

#### 4.4 — Operational Units Generation

Le système génère des Operational Units initiales.

*Les Units servent à :*

- contextualiser les situations
- améliorer le routage
- améliorer l’agrégation
- contextualiser le realtime

**<u>Exemple :</u>**

```text
Restaurant
├── Kitchen
├── Bar
├── Storage
├── Main Room
└── Terrace
```

#### 4.5 — Routing Behaviors Initialization

Le système initialise des comportements de routage opérationnels.

*Ces comportements servent à :*

- proposer des domains
- proposer des tags
- améliorer la coordination
- accélérer le runtime

**<u>Exemple :</u>**

```text
Vocabulary
        ↓
Runtime Tags
        ↓
Domains
        ↓
Routing Proposal
```

#### 4.6 — Semantic Examples Generation

Le système génère des exemples opérationnels contextualisés.

*Ces exemples servent à :*

- expliquer le fonctionnement runtime
- accélérer la prise en main
- illustrer les situations opérationnelles

**<u>Exemple :</u>**

```text
“La plonge déborde”
        ↓
Domains :
- maintenance
- hygiene

Runtime Tags :
- kitchen
- overflow
- water_issue
```

## 5 — Onboarding Wizard

#### 5.1 — Organization Creation

L’utilisateur crée l’Organization globale.

*Cette étape initialise :*

- le scope global
- la gouvernance
- les établissements futurs

#### 5.2 — Establishment Runtime Creation

Le système crée le runtime opérationnel établissement.

*Cette création initialise :*

- les feeds runtime
- le contexte IA
- la mémoire opérationnelle
- les websocket scopes
- les structures de visibilité

**<u>Runtime Initialization :</u>**

```text
Establishment Created
        ↓
Runtime Context
        ↓
Realtime Context
        ↓
Operational Bootstrap
```

#### 5.3 — Operational Modules Selection

Les modules opérationnels sont :

- proposés automatiquement
- modifiables manuellement
- activables individuellement

#### 5.4 — Structure Validation

L’utilisateur valide :

- les modules
- les units
- le vocabulaire
- les suggestions runtime

#### 5.5 — Runtime Coordination Validation

L’utilisateur valide :

- les domains initiaux
- les coordinations proposées
- les comportements runtime principaux

#### 5.6 — Manager Invitation

Les managers initiaux sont invités dans le runtime opérationnel.

*Ils reçoivent :*

- leurs domains
- leurs scopes runtime
- leurs feeds
- leurs subscriptions realtime

#### 3.4.7 — Initial Runtime Activation

Le système devient immédiatement utilisable après activation.

*Le runtime peut maintenant :*

- recevoir des Observations
- générer des Signals
- diffuser les feeds realtime
- coordonner les équipes

## 6 — Progressive Runtime Enrichment

#### 6.1 — Real Observations

Le véritable enrichissement runtime commence avec les premières remontées terrain.

*Les Observations réelles permettent :*

- d’enrichir le vocabulaire
- d’affiner les routages
- d’améliorer les tags
- d’améliorer les patterns runtime

#### 6.2 — Routing Corrections

Les corrections humaines enrichissent progressivement les comportements de routage.

**<u>Exemple :</u>**

```text
Signal routé :
- maintenance

Correction humaine :
- hygiene

Le runtime apprend :
- nouveau comportement de routage
```

#### 6.3 — Vocabulary Learning

*Le système apprend progressivement :*

- les expressions locales
- les raccourcis métier
- les références implicites
- les habitudes opérationnelles

**<u>Exemple :</u>**

```text
“la plonge”
        ↓
kitchen washing area
```

#### 6.4 — Runtime Suggestions

*Le système génère des suggestions runtime à partir :*

- des usages récurrents
- des patterns observés
- des corrections humaines
- des comportements de routage

**<u>Runtime Suggestions :</u>**

```text
Observed Pattern
        ↓
Runtime Suggestion
        ↓
Human Validation
        ↓
Runtime Enrichment
```

#### 6.5 — Human Validation Workflow

*Les enrichissements runtime restent :*

- visibles
- auditables
- validables
- contrôlés humainement

**<u>Principe critique :</u>**

```text
Le runtime propose.

Les humains contrôlent.
```

## 7 — Time-To-Value Lifecycle

#### 7.1 — Quick Activation

Le système vise une activation runtime immédiate.

*L’objectif :*

- réduire le temps avant premier usage
- produire rapidement les premiers Signals
- démarrer la coordination terrain rapidement

#### 7.2 — First Operational Signal

Le premier Signal marque le véritable démarrage du runtime opérationnel.

**<u>Lifecycle :</u>**

```text
User Onboarded
        ↓
First Observation
        ↓
AI Structuring
        ↓
First Signal
        ↓
Realtime Coordination Starts
```

#### 7.3 — Immediate Operational Usage

*Une fois activé :*

- le runtime fonctionne immédiatement
- les feeds deviennent actifs
- les websocket subscriptions démarrent
- les équipes peuvent coordonner

#### 7.4 — Continuous Runtime Learning

*Le runtime s’enrichit continuellement via :*

- les Observations
- les Signals
- les corrections
- les comportements utilisateurs
- les patterns opérationnels

#### 7.5 — Progressive Operational Intelligence

Le système devient progressivement plus pertinent.

*Le runtime améliore :*

- le routage
- la contextualisation
- l’agrégation
- la supervision
- les suggestions opérationnelles

**<u>Progressive Intelligence :</u>**

```text
Initial Bootstrap
        ↓
Runtime Usage
        ↓
Operational Learning
        ↓
Better Coordination
        ↓
Progressive Operational Intelligence
```

# PARTIE 4 — OBSERVATION SYSTEM

## 1 — Observation Philosophy

L’Observation représente une remontée terrain brute validée explicitement par un utilisateur.

*L’Observation ne représente PAS :*

- une situation opérationnelle
- une tâche
- une analyse IA
- un Signal
- un workflow métier

*L’Observation représente uniquement :*

```
un input terrain brut
persisté après validation utilisateur.
```

## 2 — Observation Runtime Position

L’Observation agit comme point d’entrée du pipeline IA.

*Le système :*

- capture une remontée terrain
- persiste l’Observation
- déclenche le pipeline IA async
- structure ensuite des Signals

**<u>Runtime Flow :</u>**

```
Field Input
        ↓
Editable Runtime
        ↓
Send Validation
        ↓
Observation Created
        ↓
AI Pipeline
        ↓
Signal(s) Creation / Aggregation
```

**<u>Critical Principle :</u>**

```
L’Observation
ne structure jamais
la situation opérationnelle.
```

## 3 — Observation Creation Flows

#### 3.1 — + Signaler → Audio

```
Audio Recording
        ↓
Speech-To-Text
        ↓
Editable Text
        ↓
User Corrections
        ↓
Send
        ↓
Observation Created
        ↓
AI Pipeline
```

#### 3.2 — + Signaler → Texte

```
Editable Text
        ↓
Send
        ↓
Observation Created
        ↓
AI Pipeline
```

#### 3.3 — Checklist Task → Audio

```
Checklist Task
        ↓
Redirect to + Signaler
        ↓
Audio Recording
        ↓
Speech-To-Text
        ↓
Editable Text
        ↓
User Corrections
        ↓
Send
        ↓
Observation Created
+ Checklist Runtime Context
        ↓
AI Pipeline
```

#### 3.4 — Checklist Task → Texte

```
Checklist Task
        ↓
Redirect to + Signaler
        ↓
Editable Text
        ↓
Send
        ↓
Observation Created
+ Checklist Runtime Context
        ↓
AI Pipeline
```

## 4 — Observation Model

#### 4.1 — Observation Structure

```
Observation
├── id
├── raw_text
├── created_by
├── establishment_id
├── checklist_execution_id
├── checklist_task_id
├── created_at
└── timestamps
```

**<u>Observation Field Description :</u>**

| Champ                  | Description                    |
| ---------------------- | ------------------------------ |
| raw_text               | Texte final validé utilisateur |
| created_by             | Auteur runtime                 |
| establishment_id       | Scope runtime établissement    |
| checklist_execution_id | Exécution checklist source     |
| checklist_task_id      | ChecklistTask source           |
| created_at             | Création runtime               |

**<u>Critical Principles :</u>**

```
Une Observation
est toujours du texte validé.

Le transcript audio
n’est jamais persisté
comme objet métier.

L’audio
est un mécanisme UX,
pas une donnée métier.
```

**<u>Architecture Principle :</u>**

```
Une Observation n’est jamais modifiée après création.
```

## 5 — Checklist Runtime Context

#### 5.1 — Runtime Context Injection

Une Observation créée depuis une ChecklistTask conserve son contexte runtime.

*Le système associe :*

```
checklist_execution_id
+
checklist_task_id
```

*Ce contexte permet :*

- contextualisation IA
- routage plus précis
- agrégation plus cohérente
- supervision opérationnelle

#### 5.2 — Exemple Runtime

```
Checklist :
"Ouverture Restaurant"

Task :
"Vérifier chambre froide"

Observation :
"La chambre froide est à 14 degrés"
```

*Le pipeline IA reçoit :*

```
Observation Text
+
Checklist Runtime Context
```

Et NON uniquement :

```
texte brut isolé
```

#### 5.3 — Critical Principle

```
Le contexte checklist
enrichit l’analyse IA
sans modifier l’Observation brute.
```

## 6 — Observation Media System

#### 6.1 — Media Philosophy

Les médias restent des supports contextuels temporaires associés à une situation opérationnelle active.

Les médias :

- ne sont PAS analysés par IA
- ne sont PAS des inputs sémantiques
- servent uniquement au contexte humain opérationnel

**<u>Critical Principle :</u>**

```
Le texte reste l’unique input canonique du pipeline IA
```

#### 6.2 — ObservationMedia Structure

```
ObservationMedia
├── id
├── observation_id
├── storage_key
├── mime_type
├── file_size
├── retention_status
├── scheduled_deletion_at
├── uploaded_by
└── timestamps
```

#### 6.3 — Media Constraints

| Règle                    | Valeur |
| ------------------------ | ------ |
| Max photos               | 3      |
| Photos seules interdites | YES    |
| Compression frontend     | YES    |
| IA Vision                | NO     |
| Upload avant Send        | YES    |

#### 6.4 — Media Lifecycle

```
Photo Selected
        ↓
Temporary Upload
        ↓
Observation Created
        ↓
Media Linked
        ↓
Signal Created / Aggregated
        ↓
Operational Lifecycle
        ↓
All Related Signals
Resolved / Canceled
        ↓
Media Deletion
```

**<u>Retention Runtime Flow :</u>**

```
Signal Resolved/Canceled
        ↓
Check linked observations
        ↓
Check all linked signals status
        ↓
No active signals remaining
        ↓
Schedule media deletion
        ↓
Media deleted
```

#### 6.5 — Critical Principle

```
Les médias
persistent uniquement
tant qu’une situation
opérationnelle reste active.

Les médias
persistent tant qu’au moins
un Signal lié reste actif.
```

## 7 — ObservationProcessing System

#### 7.1 — Processing Philosophy

Le processing IA reste séparé du domaine métier Observation.

*L’Observation :*

- capture
- persiste
- transmet

*Le processing :*

- orchestre
- queue
- retry
- supervise le pipeline IA

#### 7.2 — ObservationProcessing Structure

```
ObservationProcessing
├── observation_id
├── status
├── attempts
├── last_error
├── queued_at
├── processed_at
└── timestamps
```

#### 7.3 — Processing Statuses

| Status     | Description         |
| ---------- | ------------------- |
| queued     | En attente pipeline |
| processing | Analyse IA active   |
| processed  | Pipeline terminé    |
| failed     | Erreur pipeline     |
| retrying   | Retry en cours      |

#### 7.4 — Processing Runtime Flow

```
Observation Created
        ↓
ObservationQueued
        ↓
AI Processing
        ↓
Backend Validation
        ↓
Signal Creation / Aggregation
        ↓
Processing Completed
```

#### 7.5 — Critical Principle

```
Le pipeline IA
ne bloque jamais
la persistence utilisateur.
```

#### 8 — Audio Runtime System

#### 8.1 — Audio Runtime Position

L’audio appartient uniquement au runtime UX temporaire.

*L’audio n’existe PAS :*

- dans l’Observation
- dans le domaine métier
- dans les Signals

#### 8.2 — Audio Lifecycle

```
Audio Recording
        ↓
Temporary Upload
        ↓
Speech-To-Text
        ↓
Editable Text
        ↓
Audio Deletion
```

#### 8.3 — Audio Constraints

| Constraint        | Value   |
| ----------------- | ------- |
| Max duration      | 90s     |
| Long-term storage | NO      |
| Offline           | OUT MVP |
| Multi-recording   | NO      |

#### 8.4 — Critical Principle

```
Le système
ne conserve jamais
les fichiers audio long terme.
```

## 9 — Editable Runtime

####  9.1 — Editable Runtime Philosophy

*Avant Send :*

- le texte reste modifiable
- le pipeline IA reste inactif
- aucune Observation n’existe encore

**<u>Editable Runtime Flow :</u>**

```
Draft Runtime
        ↓
Editable Text
        ↓
User Corrections
        ↓
Send Validation
```

**<u>Critical Principle :</u>**

```
Send
représente la validation
explicite utilisateur.
```

## 10 — Observation UX States

**<u>UX State Machine :</u>**

```
IDLE
    ↓
RECORDING
    ↓
UPLOADING
    ↓
TRANSCRIBING
    ↓
EDITABLE_TEXT_READY
    ↓
SENDING
    ↓
OBSERVATION_CREATED
```

**<u>UX State Description :</u>**

| State               | Description             |
| ------------------- | ----------------------- |
| idle                | Aucun draft             |
| recording           | Capture audio active    |
| uploading           | Upload audio temporaire |
| transcribing        | STT actif               |
| editable_text_ready | Texte éditable          |
| sending             | Validation backend      |
| observation_created | Observation persistée   |

## 11 — Failure Handling

#### 11.1 — Failure Philosophy

Une erreur ne doit jamais détruire l’input utilisateur.

**<u>Critical Principle :</u>**

```
Le runtime
privilégie toujours
la conservation du draft utilisateur.
```

#### 11.2 — Upload Failure

```
Upload Failure
        ↓
Draft Preserved
        ↓
Retry Available
```

#### 11.3 — STT Failure

```
STT Failure
        ↓
User Notification
        ↓
Manual Text Fallback
```

#### 11.4 — Retry Strategy

```
Failure
    ↓
Retry
    ↓
Reprocessing
    ↓
Success OR Failure
```

#### 11.5 — Timeout Constraints

| Process | Timeout         |
| ------- | --------------- |
| STT     | 10s             |
| Upload  | Backend-defined |

## 12 — Observation → AI Pipeline Boundary

#### 12.1 — Pipeline Input

*Le pipeline IA reçoit :*

```
Observation
+
Checklist Runtime Context
+
Media References
```

*Mais :*

```
Le texte
reste l’unique input
d’analyse sémantique.
```

#### 12.2 — AI Responsibilities

*Le pipeline IA peut :*

- analyser
- splitter
- catégoriser
- router
- enrichir
- agréger

*Mais ne peut jamais :*

- modifier l’Observation
- bypass backend validation
- créer visibilité runtime directement
- contrôler permissions

#### 12.3 — Runtime Boundary

```
Observation = input brut validé

Signal = situation opérationnelle structurée
```

# PART 5 — AI STRUCTURING PIPELINE

## 1 — AI Pipeline Overview

#### 1.1 — Pipeline Philosophy

Le pipeline IA transforme une Observation brute en situations opérationnelles structurées.

*Le pipeline :*

- analyse le texte
- injecte le contexte runtime
- détecte les domains
- sépare les situations
- agrège les Signals similaires
- produit des Signals supervisables

*Le pipeline ne :*

- contrôle jamais les permissions
- ne persiste jamais directement
- ne bypass jamais les validations backend
- ne contrôle jamais la visibilité runtime

#### 1.2 — Global Runtime Flow

```txt
Observation Created
        ↓
Runtime Context Injection
        ↓
Semantic Analysis
        ↓
Domain Detection
        ↓
Situation Split
        ↓
Aggregation Engine
        ↓
Signal Creation / Aggregation
        ↓
ObservationSignalLink
        ↓
Backend Validation
        ↓
Realtime Broadcast
```

#### 1.3 — Async Pipeline

Le pipeline fonctionne entièrement en async.

*L’objectif :*

- ne jamais bloquer la persistence utilisateur
- absorber les pics runtime
- isoler les traitements IA
- permettre retry et supervision

**<u>Critical Principle :</u>**

```txt
L’Observation
est persistée immédiatement.

Le pipeline IA
travaille ensuite en arrière-plan.
```

#### 1.4 — Queue Processing

```txt
ObservationCreated
        ↓
ObservationQueued
        ↓
Worker Pickup
        ↓
AI Processing
        ↓
Processing Result
```

#### 1.5 — AI Boundaries

| Responsabilité           | IA   | Backend   |
| ------------------------ | ---- | --------- |
| Compréhension sémantique | YES  | NO        |
| Détection domains        | YES  | VALIDATES |
| Split situations         | YES  | VALIDATES |
| Aggregation suggestion   | YES  | VALIDATES |
| Permissions              | NO   | YES       |
| Visibility               | NO   | YES       |
| Persistence              | NO   | YES       |
| Feed broadcast           | NO   | YES       |

## 2 — Runtime Context Injection

#### 2.1 — Runtime Context Philosophy

Le pipeline n’analyse jamais une Observation isolée.

*Le pipeline reçoit :*

```txt
Observation
+
Establishment Runtime Context
+
Checklist Runtime Context (optional)
```

*Le contexte runtime améliore :*

- compréhension sémantique
- détection domains
- agrégation
- split
- routage opérationnel

#### 2.2 — Establishment Runtime Context

*Le contexte établissement provient :*

- onboarding
- runtime vocabulary
- operational modules
- runtime tags
- historique runtime

**<u>Example :</u>**

```txt
Establishment :
Mama Shelter Paris

Runtime Vocabulary :
- "la plonge"
- "roof"
- "PC sécurité"
- "local froid"
```

#### 2.3 — Checklist Runtime Context

Une Observation provenant d’une ChecklistTask conserve :

```txt
checklist_execution_id
+
checklist_task_id
```

*Le pipeline peut ainsi comprendre :*

- contexte opérationnel
- routine active
- zone inspectée
- intention opérationnelle

#### 2.4 — Runtime Vocabulary Injection

Le runtime vocabulary est injecté dans le contexte IA.

**<u>Example :</u>**

```txt
Observation :
"La plonge déborde"

Injected Runtime Vocabulary :
"plonge" = kitchen washing area
```

#### 2.5 — Operational Modules Injection

Les modules établissement enrichissent le contexte sémantique.

**<u>Example :</u>**

```txt
Operational Modules
├── Hotel
├── Restaurant
└── Rooftop
```

*Le pipeline adapte alors :*

- vocabulary
- routing
- split
- aggregation

#### 2.6 — Runtime Tags Injection

Les runtime tags connus enrichissent également le contexte.

**<u>Example :</u>**

```txt
Known Runtime Tags
- kitchen
- overflow
- humidity
- food_service
```

## 3 — Semantic Analysis

#### 3.1 — Operational Understanding

*Le pipeline tente d’interpréter :*

- le problème réel
- les zones concernées
- les équipes concernées
- la gravité potentielle
- les situations implicites

#### 3.2 — Contextual Interpretation

Le même texte peut produire des résultats différents selon le contexte runtime.

**<u>Example :</u>**

```txt
"La plonge déborde"
```

*Restaurant :*

```txt
kitchen washing area overflow
```

*Hotel :*

```txt
low confidence interpretation
```

#### 3.3 — Runtime Semantic Matching

*Le pipeline compare :*

- vocabulaire runtime
- aliases connus
- patterns historiques
- runtime memory

#### 3.4 — Semantic Resolution

Le pipeline produit une interprétation structurée :

```txt
{
  "domains": ["maintenance", "hygiene"],
  "tags": ["kitchen", "overflow"],
}
```

## 4 — Domain Detection

#### 4.1 — Domain Resolution

Le pipeline détecte les domains potentiellement concernés.

**<u>Example :</u>**

```txt
Observation :
"Fuite eau dans la cuisine"

Detected Domains :
- maintenance
- hygiene
```

#### 4.2 — Cross-Domain Detection

Une même situation peut concerner plusieurs domains.

**<u>Example :</u>**

```txt
"Un client a glissé sur une fuite"

Detected Domains :
- maintenance
- security
- guest_experience
```

#### 4.3 — Domain Prioritization

Le pipeline ordonne les domains selon :

- pertinence sémantique
- contexte runtime
- patterns historiques
- vocabulaire runtime

#### 4.4 — Runtime Domain Validation

Les domains détectés sont validés par le backend.

*Le backend vérifie :*

- domains autorisés
- domains existants
- cohérence runtime
- règles établissement

## 5 — Multi-Signal Split

#### 5.1 — Situation Separation

Une Observation peut contenir plusieurs situations distinctes.

**<u>Example :</u>**

```txt
"La chambre 312 n’a plus d’eau chaude
et le couloir sent fortement le gaz."
```

Le pipeline peut produire :

```txt
Signal A :
water issue

Signal B :
gas / security issue
```

#### 5.2 — Split Heuristics

Le pipeline tente d’identifier si une Observation contient :

- une seule situation opérationnelle
- plusieurs situations distinctes

*Le split ne repose PAS uniquement sur :*

- ponctuation
- phrases
- grammaire

*Le split repose principalement sur :*

- séparation sémantique
- incompatibilité opérationnelle
- différence de domains
- différence de zones
- différence de nature d’incident

**<u>A — Different Operational Situations :</u>**

```
"Le rooftop n’a plus de musique
et la chambre 312 n’a plus d’eau chaude."
```

*Situations détectées :*

```
A :
rooftop audio issue

B :
room plumbing issue
```

*Pourquoi split :*

- zones différentes
- domains différents
- interventions différentes

**<u>B — Different Domains :</u>**

```
"Le client est agressif
et il y a une fuite d’eau."
```

*Domains détectés :*

```
A :
security

B :
maintenance
```

*Pourquoi split :*

- workflows opérationnels différents
- équipes différentes
- urgence différente

**<u>C — Different Operational Units :</u>**

```
"Le parking B2 est inondé
et la cuisine sent le gaz."
```

*Pourquoi split :*

- unités opérationnelles différentes
- situations indépendantes
- risques différents

**<u>Split Rejection Cases :</u>**

Le pipeline évite le split lorsque plusieurs phrases décrivent :

- une même cause
- une même situation
- une même évolution runtime

**<u>Example — No Split :</u>**

```
"Le plafond fuit
et le sol est trempé."
```

*Pourquoi :*

```
même situation opérationnelle.
```

```
"La chambre 312 est très chaude
la climatisation semble HS."
```

*Pourquoi :*

```
même problème opérationnel.
```

#### 5.3 — Max Signal Constraints

Le pipeline limite volontairement le nombre de Signals.

**<u>Current Constraint :</u>**

| Constraint                  | Value |
| --------------------------- | ----- |
| Max signals per observation | 5     |

#### 5.4 — Backend Split Validation

Le backend valide les propositions de split avant création des Signals.

Le backend ne cherche PAS à “recomprendre” le texte.

Le backend applique des règles déterministes de sécurité runtime.

**<u>Validation Goals :</u>**

Le backend protège contre :

- sur-splitting
- duplication abusive
- incohérences runtime
- structures invalides
- outputs IA impossibles

**<u>Validation Rules :</u>**

*A — Max Signal Constraint*

```
1 Observation
cannot create
more than 5 Signals.
```

*B — Empty Situation Rejection*

*Le backend refuse :*

```
Signal
without:
- title
- domains
- semantic content
```

*C — Duplicate Split Rejection*

*Le backend refuse :*

```
2 generated Signals
with near-identical semantic meaning.
```

**<u>Example :</u>**

*IA Output :*

```
Signal A :
"Water leak kitchen"

Signal B :
"Kitchen water leakage"
```

*Backend :*

```
duplicate semantic situation
→ split rejected
```

*D — Invalid Domain Rejection*

*Le backend refuse :*

```
domains inexistants
ou interdits runtime.
```

*E — Runtime Scope Validation*

*Le backend vérifie :*

- établissement actif
- domains autorisés
- runtime context valide
- checklist context valide

*F — Conservative Fallback*

*En cas de doute :*

```
le backend privilégie :
- moins de split
- moins de Signals
- moins de duplication
```

## 6 — Signal Aggregation Engine

#### 6.1 — Aggregation Philosophy

Le système réduit le bruit opérationnel via agrégation runtime.

*Le but :*

- éviter les doublons
- centraliser les situations
- améliorer supervision
- réduire charge mentale

#### 6.2 — Similarity Detection

Le pipeline compare les nouvelles situations avec les Signals actifs.

*Le matching utilise :*

- similarité sémantique
- runtime tags
- contexte établissement
- operational patterns
- domains
- historique runtime

#### 6.3 — Active Signal Matching

```txt
New Situation
        ↓
Search Active Signals
        ↓
Similarity Scoring
        ↓
Aggregation Decision
```

#### 6.4 — Aggregation Scoring

Le pipeline calcule un score de proximité runtime.

**<u>Example :</u>**

```txt
Signal actif :
"Humidité forte accueil"

Nouvelle Observation :
"Le sol de l’accueil est encore humide"

Aggregation Score :
92%
```

#### 6.5 — Aggregation Thresholds

| Score             | Action             |
| ----------------- | ------------------ |
| High confidence   | Aggregate          |
| Medium confidence | Backend validation |
| Low confidence    | Create new Signal  |

#### 6.6 — Aggregation Rejection

*Le système refuse l’agrégation si :*

- situations réellement différentes
- urgences incompatibles
- zones incohérentes
- contexts incompatibles

#### 6.7 — ObservationSignalLink Creation

Lors d’une agrégation :

```txt
Observation
        ↓
Existing Signal
        ↓
ObservationSignalLink Created
```

#### 6.8 — Signal Count Increment

Le Signal agrégé incrémente :

```txt
signal_count
```

*Cela permet :*

- supervision
- importance runtime
- analytics
- priorisation opérationnelle

#### 6.9 — Cross-Domain Aggregation

Une agrégation peut concerner plusieurs domains.

**<u>Example :</u>**

```txt
Signal :
"Fuite eau cuisine"

Domains :
- maintenance
- hygiene
```

## 7 — Observation Signal Relationship

#### 7.1 — ObservationSignalLink Philosophy

Le système conserve une traçabilité complète entre :

- Observations
- Signals

#### 7.2 — ObservationSignalLink Structure

```txt
ObservationSignalLink
├── observation_id
├── signal_id
├── created_by_pipeline
├── created_at
└── timestamps
```

#### 7.3 — One Observation → Many Signals

```txt
One Observation
        ↓
Multiple Situations
        ↓
Multiple Signals
```

#### 7.4 — Many Observations → One Signal

```txt
Multiple Observations
        ↓
Same Operational Situation
        ↓
One Shared Signal
```

#### 7.5 — Traceability

*Le link permet :*

- audit pipeline
- supervision IA
- explainability
- analytics
- debugging runtime

#### 7.6 — Media Retention Dependency

Les médias persistent tant qu’au moins un Signal lié reste actif.

```txt
Observation Media
        ↓
Linked Signals
        ↓
All Signals Resolved/Canceled
        ↓
Media Deletion Scheduled
```

## 8 — Confidence Scoring

Le pipeline associe un score de confiance aux domains détectés.

*Le score représente :*

```
la probabilité qu’un domain
soit réellement concerné
par la situation détectée.
```

#### 8.1 — Confidence Resolution

*Le pipeline produit :*

```
{
  "maintenance": 0.92,
  "hygiene": 0.71,
  "security": 0.18
}
```

#### 8.2 — Domain Selection Threshold

Le backend conserve uniquement les domains :

```
score >= 0.5
```

**<u>Example :</u>**

```
{
  "maintenance": 0.92,
  "hygiene": 0.71,
  "security": 0.18
}
```

*Résultat runtime : :*

```
Detected Domains
- maintenance
- hygiene
```

*Rejected :*

```
security
```

#### 8.3 — Conservative Runtime Philosophy

*Le système privilégie :*

- moins de domains
- domains fortement pertinents
- réduction du bruit runtime

**<u>Critical Principle :</u>**

```
Un mauvais domain
crée du bruit opérationnel.
```

#### 8.4 — Backend Confidence Validation

*Le backend valide :*

- format des scores
- cohérence runtime
- domains autorisés
- seuil minimal

*Le backend refuse :*

- scores invalides
- domains inconnus
- confidence malformed

## 9 — Routing Rationale

#### 9.1 — Explainability Snapshot

Le système conserve un résumé explicatif runtime.

**<u>Example :</u>**

```txt
Detected :
- maintenance
- hygiene

Reason :
- "fuite"
- "eau"
- "sol humide"
```

#### 9.2 — Human-Readable Routing Explanation

*Les managers peuvent comprendre :*

- pourquoi un Signal existe ?
- pourquoi il a été routé ?
- pourquoi il a été agrégé ?

#### 9.3 — Operational Transparency

*L’objectif :*

- éviter effet boîte noire
- faciliter confiance runtime
- faciliter debugging

## 10 — Backend Validation Layer

#### 10.1 — Validation Philosophy

Le backend reste l’autorité runtime unique.

Le pipeline propose.

Le backend décide.

#### 10.2 — Schema Validation

*Le backend valide :*

- structure JSON
- domains
- tags
- formats
- constraints runtime

#### 10.3 — Hallucination Protection

*Le backend refuse :*

- domains inconnus
- structures invalides
- tags interdits
- outputs incohérents

#### 10.4 — Confidence Validation

*Le backend applique :*

- seuils runtime
- règles fallback
- stratégies conservative

#### 10.5 — Aggregation Checks

*Le backend vérifie :*

- cohérence aggregation
- compatibilité runtime
- active signals validity

#### 10.6 — Subscription Resolution

La visibilité runtime est entièrement backend-resolved.

```txt
Detected Domains
        ↓
Domain Subscriptions
        ↓
Authorized Users
        ↓
Realtime Broadcast
```

## 11 — Runtime Semantic Enrichment

#### 11.1 — Runtime Pattern Detection

Le système détecte progressivement :

- vocabulaire fréquent
- routages fréquents
- patterns récurrents
- comportements runtime

#### 5.11.2 — Vocabulary Enrichment

**<u>Example :</u>**

```txt
Observed Term :
"roof"

Resolved Meaning :
rooftop
```

#### 11.3 — Runtime Suggestions

*Le système peut proposer :*

- nouveaux aliases
- nouveaux patterns
- nouveaux routages
- nouveaux runtime tags

#### 11.4 — Human Validation Workflow

Aucun enrichissement n’est appliqué automatiquement.

```txt
Runtime Suggestion
        ↓
Human Validation
        ↓
Runtime Activation
```

#### 11.5 — Runtime Operational Memory

*Le runtime conserve progressivement :*

- vocabulary
- aliases
- routing behaviors
- aggregation patterns

## 12 — Pipeline Event Architecture

#### 12.1 — Pipeline Events

```txt
ObservationCreated
ObservationQueued
AIProcessingStarted
SemanticAnalysisCompleted
SplitCompleted
SignalCreated
SignalAggregated
ObservationLinkedToSignal
ProcessingCompleted
ProcessingFailed
```

#### 12.2 — Event Flow

```txt
ObservationCreated
        ↓
ObservationQueued
        ↓
AIProcessingStarted
        ↓
SemanticAnalysisCompleted
        ↓
SplitCompleted
        ↓
SignalCreated / SignalAggregated
        ↓
ObservationLinkedToSignal
        ↓
ProcessingCompleted
```

## 13 — AI Architecture Principles

```txt
Permissions
remain backend-controlled.
```

```txt
The AI pipeline
never writes directly
to the database.
```

```txt
Runtime enrichment
remains human-controlled.
```

```txt
The backend
remains the single
runtime authority.
```

# PARTIE 6 — SIGNAL SYSTEM

## 1 — Signal Philosophy

Le Signal représente une situation opérationnelle active supervisée collectivement.

*Le Signal centralise progressivement :*

- Observations
- Actions
- commentaires
- événements runtime
- escalades
- changements de priorité
- coordination multi-domain

## 2 — Signal Architecture

#### 2.1 — Signal Structure

```txt
Signal
├── id
├── title
├── description
├── detected_domains[]
├── runtime_tags[]
├── urgency
├── pinned
├── status
├── signal_count
├── created_from_observation_id
├── created_at
└── timestamps
```

#### 2.2 — detected_domains[]

Les detected_domains représentent les domains détectés par le pipeline IA lors de la création du Signal.

*Ils servent à :*

- coordination runtime
- subscriptions
- feed filtering
- notifications
- realtime visibility

**<u>Example :</u>**

```txt
Detected Domains
- maintenance
- hygiene
```

#### 2.3 — runtime_tags[]

Les runtime_tags représentent des labels contextuels flexibles.

Ils servent à :

- enrichir le Signal
- améliorer aggregation
- améliorer analytics
- améliorer recherche runtime

**<u>Example :</u>**

```txt
[
  "water_leak",
  "kitchen",
  "humidity"
]
```

#### 2.4 — urgency

L’urgence représente la criticité opérationnelle de la situation.

Example

```txt
medium
high
```

*L’urgence influence :*

- feed ordering
- notifications
- supervision
- escalations

#### 2.5 — pinned

Le pinning force une visibilité élevée dans le Signal Feed.

*Le pinning ne modifie PAS :*

- le lifecycle
- la priorité métier
- la résolution

**<u>Critical Principle :</u>**

```txt
Pinning = visibility mechanism
NOT
business status.
```

#### 2.7 — status

Le status représente l’état runtime global du Signal.

**<u>Supported Statuses :</u>**

```txt
open
in_progress
resolved
canceled
archived
```

## 3 — Signal Lifecycle

#### 3.1 — open

Le Signal est actif mais aucun plan d’action n’existe encore.

**<u>Runtime Meaning :</u>**

```txt
Situation detected
without operational execution yet.
```

#### 3.2 — in_progress

Au moins une Action existe

**<u>Transition :</u>**

```txt
Action Created
        ↓
Signal → in_progress
```

#### 3.3 — resolved

La situation est considérée comme résolue opérationnellement.

**<u>Resolution Rules :</u>**

Le Signal devient resolved lorsque :

- toutes les Actions sont done/canceled
  OR
- un manager résout manuellement

#### 3.4 — canceled

Le Signal est annulé volontairement.

**<u>Example :</u>**

```txt
false alert
duplicate
invalid situation
```

#### 3.5 — archived

Le Signal quitte le runtime actif.

Un Signal archived :

- n’apparaît plus dans les feeds actifs
- reste historisé
- reste consultable
- reste utilisable pour analytics

## 4 — Signal Visibility

#### 4.1 — Domain Subscription Resolution

La visibilité runtime repose sur :

```txt
domain subscriptions.
```

*Le backend résout :*

- detected_domains
- subscriptions
- runtime permissions
- établissement actif

**<u>Runtime Flow :</u>**

```txt
Detected Domains
        ↓
Subscription Resolution
        ↓
Authorized Users
        ↓
Realtime Broadcast
```

#### 4.2 — Feed Visibility

Un Signal apparaît uniquement si :

- l’utilisateur possède une subscription compatible
- l’établissement actif correspond
- les règles backend autorisent la visibilité

#### 4.3 — Realtime Visibility

Chaque événement runtime applique :

- filtering backend
- websocket filtering
- subscription filtering

**<u>Critical Principle :</u>**

```txt
Realtime
never bypasses
backend visibility rules.
```

#### 4.4 — Cross-Domain Visibility

Un même Signal peut être visible par plusieurs domains simultanément.

**<u>Example :</u>**

```txt
Signal:
water leak kitchen

Visible To:
- maintenance
- hygiene
- security
```

## 5 — Signal Aggregation Runtime

#### 5.1 — Aggregated Signal Philosophy

Le Signal agrégé représente une situation partagée enrichie progressivement.

*Le système évite :*

- duplication runtime
- fragmentation supervision
- surcharge opérationnelle

#### 5.2 — signal_count

Le signal_count représente le nombre situation agrégées dans le Signal.

**<u>Example :</u>**

```txt
Signal :
"Humidité accueil"

signal_count :
12
```

*Cela indique :*

- fréquence runtime
- importance opérationnelle
- persistance terrain

### 5.3 — Observation References

Le Signal conserve les références vers les Observations liées via :

```txt
ObservationSignalLink
```

#### 5.4 — Aggregation Timeline

Chaque agrégation produit un événement runtime.

**<u>Example :</u>**

```txt
Signal Created
        ↓
Observation Aggregated
        ↓
signal_count incremented
        ↓
Realtime Feed Update
```

## 6 — Signal Priority & Pinning System

#### 6.1 — Pinning Philosophy

Le pinning maintient certaines situations visibles durablement.

*Le pinning sert à :*

- supervision
- vigilance
- information collective
- suivi continu

**<u>Example :</u>**

```txt
- humidité persistante
- ascenseur fragile
- vigilance météo
- travaux temporaires
```

#### 6.2 — Signal Feed Ordering

```txt
Pinned Signals
        ↓
High Urgency Signals
        ↓
Open Signals
        ↓
In Progress Signals
        ↓
Resolved Signals
```

#### 6.3 — Pinning Rules

*Le pinning :*

- reste manuel
- peut être activé/désactivé
- ne modifie jamais le lifecycle

#### 6.4 — Pinned Signal Lifecycle

```txt
Manager pins Signal
        ↓
Signal moves to top
        ↓
Realtime Feed Update
        ↓
Pinned visibility maintained
```

#### 6.5 Urgency

L’urgence représente le niveau de visibilité opérationnelle d’un Signal.

L’urgence est entièrement contrôlée manuellement par :

- manager
- director

Le pipeline IA ne contrôle jamais l’urgence.

**<u>Supported Values :</u>**

| Value  | Meaning            |
| ------ | ------------------ |
| medium | situation standard |
| high   | situation urgente  |

**<u>Runtime Effects :</u>**

*L’urgence influence :*

- ordering du Signal Feed
- visibilité runtime
- notifications
- supervision opérationnelle

**<u>Critical Principle :</u>**

```
Urgency
remains human-controlled.
```

## 7 — Signal Feed Architecture

#### 7.1 — Supervisory Feed Philosophy

Le Signal Feed sert à :

- superviser les situations
- coordonner les domains
- suivre les urgences
- maintenir visibilité runtime

*Le feed ne sert PAS à :*

- exécuter les interventions
- gérer accountability

#### 7.2 — Signal Feed Structure

**<u>Feed Runtime Philosophy :</u>**

Le feed doit permettre à un manager de comprendre immédiatement :

- ce qui nécessite attention ?
- quelles situations sont urgentes ?
- quelles situations persistent ?
- quelles équipes sont impliquées ?
- quelles situations évoluent en temps réel ?

**<u>Feed Sections :</u>**

```txt
Signal Feed
├── Pinned Signals
├── Active Signals
├── Resolved Signals
└── Archived History
```

**<u>Feed Runtime Philosophy :</u>**

Le feed doit permettre à un manager de comprendre immédiatement :

- ce qui nécessite attention ?
- quelles situations sont urgentes ?
- quelles situations persistent ?
- quelles équipes sont impliquées ?
- quelles situations évoluent en temps réel ?

#### 7.3 — Feed Realtime Updates

Le feed est mis à jour via websocket runtime.

**<u>Runtime Events :</u>**

```txt
SignalCreated
SignalAggregated
SignalUpdated
SignalPinned
SignalResolved
```

#### 7.4 — Feed Sorting Rules

Le feed priorise les situations nécessitant le plus d’attention opérationnelle.

Le sorting runtime est dynamique.

*Chaque événement runtime peut provoquer :*

- repositionnement
- remontée feed
- réorganisation supervisionnelle

**<u>Global Sorting Order :</u>**

```
Pinned Signals
        ↓
High Urgency Signals
        ↓
Recently Updated Signals
        ↓
Open Signals
        ↓
In Progress Signals
        ↓
Resolved Signals
```

**<u>Sorting factory :</u>** 

| Critère            | Impact               |
| ------------------ | -------------------- |
| pinned             | priorité absolue     |
| urgency            | visibilité élevée    |
| signal_count       | importance runtime   |
| recent aggregation | activité récente     |
| lifecycle status   | organisation globale |

**<u>Global Sorting Order :</u>**

```
Pinned Signals
        ↓
High Urgency Signals
        ↓
Recently Updated Signals
        ↓
Open Signals
        ↓
In Progress Signals
        ↓
Resolved Signals
```

**<u>signal_count Influence :</u>**

Un Signal fortement agrégé devient plus visible.

*Example*

```
Signal A :
signal_count = 2

Signal B :
signal_count = 18
```

#### 7.5 — Feed Visibility Filtering

Le Signal Feed est entièrement filtré backend-side.

Le frontend ne résout jamais :

- permissions
- subscriptions
- visibilité runtime

**<u>Visibility Resolution Flow :</u>**

```
Signal
        ↓
Detected Domains
        ↓
Subscription Resolution
        ↓
Authorized Users
        ↓
Realtime Feed Delivery
```

**<u>Feed Filtering Dimensions :</u>**

*Le backend filtre selon :*

| Dimension            | Usage                 |
| -------------------- | --------------------- |
| active_establishment | isolation runtime     |
| domain subscriptions | visibilité principale |
| role permissions     | accès runtime         |
| signal status        | filtering feed        |
| archived visibility  | historique            |

**<u>Domain Subscription Filtering :</u>**

Un utilisateur voit uniquement les Signals compatibles avec ses subscriptions domain.

*Example*

```
User subscriptions:
- maintenance
- hygiene

Signal domains:
- maintenance
- guest_experience
```

*Résultat :*

```
Signal visible
because:
maintenance matches.
```

**<u>Multi-Domain Visibility :</u>**

Un même Signal peut être visible simultanément par plusieurs équipes.

*Example*

```
Signal:
water leak kitchen

Detected Domains:
- maintenance
- hygiene
- security
```

*Visible dans :*

- feed maintenance
- feed hygiene
- feed security

**<u>Realtime Filtering :</u>**

*Chaque websocket broadcast applique :*

- establishment filtering
- subscription filtering
- runtime permission filtering

**<u>Critical Principle :</u>**

```
Realtime updates
never bypass
backend filtering.
```

**<u>Feed Isolation Principle :</u>**

Le runtime d’un établissement reste totalement isolé.

```
Users
never receive Signals
outside their active establishment.
```

**<u>Visibility Runtime Goal :</u>**

*Le filtering runtime doit garantir :*

- faible bruit supervisionnel
- pertinence opérationnelle
- isolation établissement
- coordination multi-domain contrôlée
- sécurité runtime déterministe

## 8 — Signal Realtime Coordination

#### 8.1 — Live Insertion

Les nouveaux Signals apparaissent dynamiquement dans le feed.

**<u>Runtime Flow :</u>**

```txt
Signal Created
        ↓
Visibility Resolution
        ↓
Realtime Broadcast
        ↓
Live Feed Insertion
```

#### 8.2 — Feed Updates

Les événements runtime mettent à jour :

- ordering
- urgency
- signal_count
- active domains
- escalations

#### 8.3 — Notifications

*Le Signal peut produire :*

- push notifications
- realtime notifications
- manager alerts

## 9 — Signal Timeline Architecture

#### 9.1 — Timeline Philosophy

Le Signal construit progressivement une timeline opérationnelle vivante.

*La timeline centralise :*

- Observations
- aggregations
- comments
- Actions
- lifecycle changes

#### 9.2 — Timeline Events

```txt
Signal Created
Signal Aggregated
Signal Comment Added
Action Created
Action Accepted
Action Comment Added
Action Reopened
Action Validated
Action Canceled
Signal Resolved
Signal Canceled
```

#### 9.3 — Aggregation Events

Chaque nouveau Signal agrégée enrichit la timeline.

**<u>Example :</u>**

```txt
+1 Signal aggregated
        ↓
signal_count updated
        ↓
Timeline updated
```

#### 9.4 — Action Events

Les événements Action apparaissent dans le contexte du Signal.

**<u>Example :</u>**

```txt
Action Created
Action Accepted
Action Done
Action Reopened
Action Validated
Action Canceled
Action Comment Added
```

#### 9.6 — Realtime Timeline Updates

La timeline se met à jour dynamiquement via websocket runtime.

## 10 — Signal Architecture Principles

**<u>Shared Operational Context</u>**

```txt
Signals
represent shared operational situations.
```

**<u>Multi-Domain Collaboration</u>**

```txt
Multiple domains
can coordinate simultaneously
on the same Signal.
```

**<u>No Strong Ownership</u>**

```txt
Signals
remain shared coordination objects.
```

**<u>Pinning ≠ Status</u>**

```txt
Pinning
is a visibility mechanism,
not a business lifecycle state.
```

# PART 7 — ACTION EXECUTION SYSTEM

## 1 — Action Philosophy

#### 1.1 — Action = Operational Accountability

Une Action représente une intervention opérationnelle explicite avec responsabilité humaine.

*Le Signal représente :*

```txt
la situation opérationnelle.
```

*L’Action représente :*

```txt
le travail concret
à exécuter.
```

#### 1.2 — Executable Operational Work

Une Action existe lorsqu’une intervention concrète devient nécessaire.

*Une Action peut représenter :*

- inspection
- réparation
- nettoyage
- sécurisation
- validation
- intervention terrain

## 2 — Action Architecture

#### 2.1 — Action Structure

```txt
Action
├── id
├── title
├── description
├── signal_id
├── assigned_to
├── created_by
├── operational_domain
├── status
├── validation_required
├── validated_by
├── due_at
├── created_at
└── timestamps
```

#### 2.2 — Assignment

Chaque Action possède un responsable opérationnel explicite.

*L’assignment représente :*

```txt
qui doit exécuter
l’intervention.
```

#### 2.3 — Operational Responsibility

L’Action crée une responsabilité runtime explicite.

*Contrairement au Signal :*

```txt
l’Action
n’est pas un objet partagé sans responsable.
```

#### 2.4 — Validation

Les Actions nécessitent une validation manager avant clôture finale.

#### 2.5 — Domain Context

Chaque Action conserve un domain principal.

*Le domain sert à :*

- coordination
- filtering
- notifications
- workload supervision

## 3 — Action Lifecycle

#### 3.1 — open

L’Action existe mais l’intervention n’a pas encore commencé.

**<u>Runtime Meaning :</u>**

```txt
Work identified
but not started yet.
```

#### 3.2 — in_progress

L'assignee a acceté l'action et l'intervention réelle est en cours.

**<u>Runtime Transition :</u>**

```txt
User accept & starts intervention
        ↓
Action → in_progress
```

#### 3.3 — pending_validation

L’intervention est terminée côté terrain mais attend validation manager.

**<u>Runtime Flow :</u>**

```txt
Assignee marks work completed
        ↓
Action → pending_validation
```

#### 3.4 — done

L’intervention est officiellement validée et terminée.

#### 3.5 — canceled

L’intervention devient inutile ou invalide.

**<u>Examples :</u>**

```txt
- duplicate intervention
- false alert
- operational change
```

#### 3.6 — reopened

Une Action en attente de validation peut être réouverte.

**<u>Example :</u>**

```txt
Repair pending_validation
        ↓
Issue persists
        ↓
Action reopened
```

**<u>Lifecycle Flow :</u>**

```txt
OPEN
    ↓
IN_PROGRESS
    ↓
PENDING_VALIDATION
    ↓
DONE

Alternative states:
CANCELED
REOPENED
```

## 4 — Execution Feed Architecture

#### 4.1 — Execution Feed Philosophy

Le Action Feed représente l’espace d’exécution opérationnelle.

*Le feed sert à :*

- suivre le travail terrain
- superviser la charge opérationnelle
- suivre les validations
- distribuer les interventions

*Le Action Feed ne sert PAS à :*

- supervision globale établissement
- agrégation situationnelle
- coordination supervisionnelle

*Cela appartient au Signal Feed.*

*Le feed centralise :*

- Actions
- ChecklistExecutions

#### 4.2 — Execution Feed Structure

```txt
Execution Feed
├── My Active Actions
├── My Active Checklists
├── Team Active Execution
├── Pending Validation Queue
├── Recently Completed
└── Canceled Execution
```

**<u>My Active Actions</u>**

Actions directement assignées à l’utilisateur actif.

**<u>Team Active Actions</u>**

Actions actives du domain ou de l’équipe supervisée.

*Utilisé principalement par :*

- managers
- directors

**<u>Pending Validation Queue :</u>**

Queue dédiée aux validations manager.

*Runtime Flow :*

```txt
Action Completed
        ↓
pending_validation
        ↓
Validation Queue
```

**<u>Recently Completed :</u>**

Actions récemment validées.

*Permet :*

- supervision récente
- contrôle qualité
- continuité opérationnelle

#### 4.3 — Assignment Visibility

La visibilité dépend principalement :

- assignment utilisateur
- operational domain
- rôle runtime
- établissement actif

**<u>Visibility Example :</u>**

```txt
Assigned User
        ↓
Action visible immediately
Manager supervising domain
        ↓
Team actions visible
```

#### 4.4 — Workload Visibility

*Les managers peuvent superviser :*

- volume d’Actions actives
- workload équipe
- validations en attente
- distribution opérationnelle

#### 4.5 — Pending Validation Queue

Les managers disposent d’une vue dédiée :

```txt
Pending Validation Queue
```

*Cette queue centralise :*

- Actions terminées
- validations requises
- contrôles qualité runtime

## 5 — Action Assignment Model

#### 5.1 — Manual User Assignment

Les Actions sont assignées manuellement.

*Le système ne réalise PAS :*

- auto-assignment
- dispatch automatique
- workload balancing IA

**<u>Critical Principle</u>**

```txt
Operational responsibility
remains human-controlled.
```

#### 5.2 — Domain Context

Chaque Action appartient à un domain principal.

**<u>Example</u>**

```txt
maintenance
security
hygiene
guest_experience
```

*Le domain améliore :*

- coordination
- filtering
- workload supervision

#### 5.3 — Cross-Domain Coordination

Une Action peut exister dans un Signal multi-domain.

**<u>Example</u>**

```txt
Signal:
water leak kitchen

Domains:
- maintenance
- hygiene

Action:
repair water pipe

Operational Domain:
maintenance
```

#### 5.4 — Assignment Reassignment

Une Action peut être réassignée par le manager 

**<u>Runtime Flow</u>**

```txt
Action Assigned
        ↓
Operational Change
        ↓
Reassignment
        ↓
Realtime Feed Update
```

## 6 — Action Validation Workflow

#### 6.1 — Validation Rules

Toutes les Actions nécessitent validation avant clôture finale.

#### 6.2 — Manager Validation

*Le manager peut :*

- valider
- réouvrir
- commenter

**<u>Validation Flow :</u>**

```txt
Action → pending_validation
        ↓
Manager Review
        ↓
DONE OR REOPENED
```

#### 6.3 — Rejection Workflow

Le manager peut refuser une validation.

**<u>Example</u>**

```txt
Repair incomplete
        ↓
Action reopened
```

#### 6.4 — Reopen Workflow

Une Action réouverte retourne dans le runtime actif.

```txt
REOPENED
        ↓
IN_PROGRESS
```

## 7 — Workload Coordination

#### 7.1 — Active Workload

*Le système supervise :*

- Actions actives
- workload utilisateur
- workload domain
- validations pending

#### 7.2 — Team Capacity

*Les managers peuvent évaluer :*

- surcharge opérationnelle
- répartition travail
- capacité équipe
- disponibilité runtime

#### 7.3 — Operational Distribution

*Le système facilite :*

- redistribution runtime
- réassignation
- équilibrage humain manuel

*Le système ne réalise PAS :*

- balancing automatique IA
- assignment autonome

## 8 — Action Timeline Architecture

#### 8.1 — Timeline Philosophy

Chaque Action possède une timeline runtime dédiée.

*La timeline centralise :*

- changements status
- commentaires
- validations
- réassignations
- événements runtime

#### 8.2 — Action Events

```txt
Action Created
Action Assigned
Action Started
Action Completed
Action Reopened
Action Validated
Action Canceled
```

#### 8.3 — Validation Events

Les validations enrichissent la timeline.

**<u>Example</u>**

```txt
Action Completed
        ↓
Manager Validation
        ↓
Validation Event Added
```

#### 8.4 — Assignment Events

Les changements assignment restent historisés.

**<u>Example</u>**

```txt
Assigned to User A
        ↓
Reassigned to User B
```

#### 8.5 — Realtime Timeline Updates

La timeline se met à jour dynamiquement via websocket runtime.

## 9 — Action Comment Scope

#### 9.1 — Scoped Comment Philosophy

Les commentaires Action restent scoped à l’Action.

*Ils ne sont PAS visibles :*

- sur les autres Actions
- globalement sur le Signal

#### 9.2 — Action Contextual Communication

*Les commentaires servent à :*

- coordination intervention
- suivi terrain
- validation
- contexte exécution

**<u>Example</u>**

```txt
"Pièce remplacée."
"Intervention retardée."
"Validation sécurité nécessaire."
```

## 10 — Action Architecture Principles

**<u>Actions Create Accountability</u>**

```txt
Actions
create explicit operational responsibility.
```

**<u>Assignment Controls Visibility</u>**

```txt
Assignment
drives execution visibility.
```

**<u>Human-Controlled Coordination</u>**

```txt
Operational execution
remains human-supervised.
```

# PART 8 — COMMUNICATION & REALTIME COORDINATION

## 1 — Communication Philosophy

#### 1.1 — Structured Operational Coordination

Houston ne repose pas sur de la communication libre globale.

La communication existe toujours dans un contexte opérationnel explicite.

*Le système privilégie :*

- coordination contextualisée
- communication supervisable
- événements traçables
- visibilité opérationnelle
- continuité runtime

**<u>Runtime Philosophy</u>**

```txt
La communication
doit enrichir
la situation opérationnelle.
```

*Et non :*

- dériver hors contexte
- créer des workflows invisibles
- contourner le runtime supervisionnel

#### 1.2 — Contextual Communication

Chaque message appartient à un contexte runtime explicite.

**<u>Supported Contexts</u>**

| Context | Usage                       |
| ------- | --------------------------- |
| Signal  | coordination situationnelle |
| Action  | coordination exécution      |
| Mention | coordination ciblée         |

#### 1.3 — Communication Boundaries

*La communication ne remplace jamais :*

- lifecycle métier
- status runtime
- validation backend
- supervision opérationnelle

*Un commentaire ne doit jamais devenir :*

```txt
un workflow caché.
```

## 2 — Contextual Comments System

#### 2.1 — Signal Comments

Les Signal Comments servent à coordonner la situation globale.

*Ils sont visibles :*

- par tous les utilisateurs autorisés sur le Signal
- dans la détail du Signal

**<u>Signal Comment Examples</u>**

```txt
"La fuite continue malgré la première intervention."

"Le problème semble toucher plusieurs chambres."

"La sécurité a isolé la zone."
```

**<u>Signal Comment Runtime Role</u>**

*Les commentaires Signal servent à :*

- partager du contexte
- coordonner plusieurs domains
- enrichir la supervision
- suivre l’évolution situationnelle

#### 2.2 — Action Comments

Les Action Comments restent strictement liés à une Action spécifique.

*Ils servent à coordonner :*

- l’intervention terrain
- l’exécution
- la validation
- les contraintes opérationnelles

**<u>Action Comment Examples</u>**

```txt
"Pièce remplacée."

"Intervention retardée."

"Validation électrique nécessaire."

"Le fournisseur arrive à 14h."
```

**<u>Critical Principle</u>**

```txt
Les commentaires Action
restent scoped
à l’Action concernée.
```

#### 2.3 — Contextual Visibility

La visibilité des commentaires dépend entièrement du contexte parent.

**<u>Signal Comment Visibility</u>**

```txt
Signal visibility
        ↓
Comment visibility
```

**<u>Action Comment Visibility</u>**

```txt
Action visibility
        ↓
Comment visibility
```

#### 2.4 — Cross-Action Context

Les commentaires Action ne sont jamais partagés automatiquement entre Actions.

*Pourquoi :*

```txt
chaque Action
représente
une responsabilité distincte.
```

**<u>Example</u>**

```txt
Action A :
réparer fuite

Action B :
nettoyer cuisine
```

## 3 — Mention System

#### 3.1 — Mention Philosophy

Les mentions permettent une coordination ciblée temps réel.

*Le système permet :*

```txt
@user
```

*dans :*

- Signal comments
- Action comments

#### 3.2 — Contextual Mentions

Une mention conserve toujours son contexte runtime.

**<u>Example</u>**

```txt
@Thomas peux-tu vérifier la chambre 312 ?
```

*Contexte :*

```txt
Signal :
water leak floor 3
```

#### 3.3 — Mention Visibility

Une mention ne bypass jamais la visibilité runtime.

**<u>Critical Principle</u>**

```txt
Mention
does not override
permissions.
```

**<u>Runtime Flow</u>**

```txt
Comment Created
        ↓
Mention Detection
        ↓
Visibility Validation
        ↓
Notification Dispatch
```

#### 3.4 — Mention Notifications

Une mention peut produire :

- push notification
- realtime notification
- badge update

## 4 — Realtime Architecture

#### 4.1 — Event-Driven Philosophy

Le realtime repose entièrement sur des business events backend.

*Le frontend ne synchronise jamais directement :*

- les états métier
- les permissions
- les lifecycle runtime

#### 4.2 — Global Realtime Flow

```txt
Business Event
        ↓
Backend Event Bus
        ↓
Visibility Resolution
        ↓
Websocket Broadcast
        ↓
Client Feed Update
```

#### 4.3 — Event Bus

Le backend centralise les événements runtime.

**<u>Example Events</u>**

```txt
SignalCreated
SignalUpdated
SignalPinned
ObservationAggregated
ActionCreated
ActionAssigned
ActionValidated
CommentAdded
MentionCreated
```

#### 4.4 — Websocket Broadcasting

Chaque websocket broadcast applique :

- establishment filtering
- subscription filtering
- permission validation
- runtime visibility

**<u>Critical Principle</u>**

```txt
Realtime
never bypasses
backend runtime rules.
```

#### 4.5 — Mobile Synchronization

Les clients mobiles reçoivent :

- insertions runtime
- updates runtime
- reorder runtime
- badge updates
- notification events

## 5 — Realtime Feed Coordination

#### 5.1 — Signal Feed Coordination

Le Signal Feed reçoit :

- nouveaux Signals
- aggregations
- changements urgence
- nouveaux commentaires
- lifecycle updates

**<u>Runtime Example</u>**

```txt
New Observation Aggregated
        ↓
signal_count updated
        ↓
Feed reordered
        ↓
Realtime UI update
```

#### 5.2 — Execution Feed Coordination

*Le Execution Feed reçoit :*

- nouvelles Actions
- ChecklistExecutions
- assignment updates
- validation updates
- workload changes

**<u>Runtime Example</u>**

```txt
Action Assigned
        ↓
Execution Feed updated
        ↓
Assigned user notified
```

#### 5.3 — Realtime Feed Reordering

Les feeds peuvent être réordonnés dynamiquement selon :

- urgence
- activité récente
- nouvelles aggregations
- validation runtime
- pinning

#### 5.4 — Badge Synchronization

Les badges runtime restent synchronisés en temps réel.

**<u>Examples</u>**

```txt
- pending validations
- assigned Actions
- mentions
```

## 6 — Notification System

#### 6.1 — Notification Philosophy

Les notifications servent à attirer l’attention opérationnelle.

*Le système évite :*

- spam
- duplication
- bruit runtime

#### 6.2 — Push Notifications

*Le système peut envoyer :*

- Action assignment
- mention
- high urgency Signal
- validation required

**<u>Example</u>**

```txt
Nouvelle Action assignée :
"Réparer fuite cuisine"
```

#### 6.3 — Operational Alerts

*Les alerts runtime concernent :*

- situations urgentes
- validations critiques
- nouvelles responsabilités

#### 6.4 — Mention Notifications

Une mention déclenche :

- push notification
- badge update
- realtime insertion

#### 6.5 — Notification Visibility

Les notifications respectent toujours :

- établissement actif
- subscriptions
- runtime permissions
- visibility filtering

**<u>Critical Principle</u>**

```txt
Les notifications
ne bypass jamais
la visibilité runtime.
```

## 7 — Offline & Resynchronization Strategy

#### 7.1 — Offline Philosophy

Le runtime mobile doit tolérer :

- pertes réseau
- interruptions websocket
- mobilité terrain

#### 7.2 — Reconnection Strategy

*Lors d’une reconnexion :*

```txt
Client reconnects
        ↓
Missed events detection
        ↓
Feed resynchronization
        ↓
Realtime resumed
```

#### 7.3 — Feed Resynchronization

*Le client peut recharger :*

- Signal Feed
- Execution Feed
- notifications
- badges
- timelines

*pour retrouver un état runtime cohérent.*

#### 7.4 — Realtime Recovery

*Le système privilégie :*

```txt
state resynchronization
over local assumptions.
```

## 8 — Event-Driven Coordination

#### 8.1 — Business Events

Le système repose sur des business events explicites.

**<u>Example</u>**

```txt
SignalCreated
ActionCreated
CommentAdded
MentionCreated
ActionValidated
SignalResolved
```

#### 8.2 — Feed Synchronization

Les feeds réagissent aux événements runtime.

```txt
Business Event
        ↓
Realtime Broadcast
        ↓
Feed Update
        ↓
UI Synchronization
```

#### 8.3 — Cross-System Updates

Un événement peut impacter plusieurs systèmes simultanément.

**<u>Example</u>**

```txt
Action Validated
        ↓
Execution Feed updated
        ↓
Signal Timeline updated
        ↓
Notification dispatched
        ↓
Badge updated
```

## 10 — Communication Architecture Principles

**<u>Signals Structure Situations</u>**

```txt
Signals
structure operational situations.
```

**<u>Actions Structure Execution</u>**

```txt
Actions
structure operational execution.
```

**<u>Communication Remains Contextual</u>**

```txt
Communication
always belongs
to an operational context.
```

**<u>Realtime Is Event-Driven</u>**

```txt
Realtime coordination
is fully event-driven.
```
