# Houston — Onboarding Domain

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Mama Shelter Nice  
**Documents liés:**  
- `Houston_mvp_cadrage_p0.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Onboarding** de Houston pour le MVP.

Il définit :
- l'objectif de l'onboarding ;
- les acteurs de l'onboarding ;
- la création Organization / Establishment ;
- les données minimales requises ;
- la description établissement ;
- le bootstrap IA ;
- la validation humaine ;
- les modules, domains, units et vocabulary initiaux ;
- les routing hints ;
- les invitations initiales ;
- les critères d'activation ;
- l'onboarding progressif post-activation ;
- les events MVP ;
- les implications backend/frontend ;
- les tests fonctionnels attendus.

Ce document sert de référence pour Product Owner, Product Designer, Tech Lead, Backend, Frontend et QA.

---

# 2. Définition métier

## 2.1 Définition

L'onboarding Houston est le processus qui initialise un établissement utilisable rapidement avec un contexte runtime minimal validé humainement.

```txt
Onboarding
= initialisation rapide d'un établissement
= bootstrap runtime minimal
= propositions IA
= validation humaine
= activation terrain
```

## 2.2 Ce que l'onboarding n'est pas

L'onboarding n'est pas :
- une modélisation exhaustive de l'organisation ;
- un paramétrage complet de tous les workflows ;
- une saisie complète de l'organigramme ;
- une configuration définitive ;
- une dépendance absolue à l'IA.

## 2.3 Objectif MVP

L'objectif MVP est de rendre un établissement opérationnel rapidement, sans chercher à représenter parfaitement toute son organisation dès le départ.

```txt
Configuration minimale
        ↓
Bootstrap IA
        ↓
Validation humaine
        ↓
Activation runtime
        ↓
Usage terrain réel
        ↓
Enrichissement progressif
```

---

# 3. Acteurs de l'onboarding

## 3.1 Pilote MVP

Pour le pilote Mama Shelter Nice :

```txt
Houston admin
+
Owner / Director côté client
```

## 3.2 Produit cible

Dans le produit cible :

```txt
Owner ou Director
```

## 3.3 Rôles concernés

Pendant l'onboarding, les rôles activables sont :

```txt
Owner
Director
Manager
```

Les Staff peuvent être invités après activation.

## 3.4 Pourquoi ne pas impliquer tout le staff dès l'onboarding

L'objectif est d'activer vite le runtime.

Inviter tout le staff dès l'onboarding :
- ralentit le setup ;
- ajoute de la friction ;
- dépend de l'organisation RH ;
- n'est pas nécessaire pour valider la structure initiale.

---

# 4. Organization / Establishment

## 4.1 Ordre de création

Décision validée :

```txt
Organization
        ↓
Establishment
```

## 4.2 Establishment belongs_to Organization

Un Establishment ne peut pas exister sans Organization.

```txt
Establishment belongs_to Organization
```

## 4.3 Définitions

| Concept | Définition |
|---|---|
| Organization | Entité juridique / groupe / client parent |
| Establishment | Runtime opérationnel réel |
| Onboarding | Initialisation du runtime d'un Establishment |

## 4.4 Scope runtime

Le runtime reste toujours scoped à l'établissement.

```txt
Establishment Runtime
├── Operational Modules
├── Operational Domains
├── Operational Units
├── Runtime Vocabulary
├── Runtime Tags
├── Routing Hints
├── Users / Memberships
└── Activation State
```

---

# 5. Données requises MVP

## 5.1 Required MVP

```txt
Required MVP
├── organization_name
├── establishment_name
├── establishment_activity_description
├── validated_operational_modules
└── initial_manager_or_director
```

## 5.2 Description des champs

| Champ | Rôle |
|---|---|
| `organization_name` | Créer le client parent |
| `establishment_name` | Créer le runtime établissement |
| `establishment_activity_description` | Alimenter le bootstrap IA |
| `validated_operational_modules` | Activer le contexte métier initial |
| `initial_manager_or_director` | Permettre la coordination humaine initiale |

## 5.3 Données non obligatoires au MVP

Ne pas rendre obligatoires :
- adresse complète ;
- téléphone ;
- horaires ;
- organigramme complet ;
- liste complète du staff ;
- toutes les rooms ;
- toutes les checklists ;
- billing Stripe ;
- logo / branding.

Ces éléments peuvent être complétés après activation.

---

# 6. Description établissement

## 6.1 Règle

La description établissement est obligatoire.

```txt
establishment_activity_description required
minimum length = 50 caractères
```

## 6.2 Format

La description est un champ libre, guidé par des exemples.

## 6.3 Exemples guidés

Texte d'aide recommandé :

```txt
Décrivez les activités de votre établissement :
- hôtel
- restaurant
- rooftop
- bar
- salles de séminaire
- zones importantes
- équipes opérationnelles
```

## 6.4 Pourquoi

La description sert à générer :
- modules ;
- domains ;
- units ;
- runtime tags ;
- vocabulary ;
- routing hints.

## 6.5 Description trop faible

Si la description fait moins de 50 caractères :
- bloquer la soumission ;
- demander plus de contexte ;
- afficher des exemples.

---

# 7. Bootstrap IA

## 7.1 Rôle de l'IA

L'IA propose une structure opérationnelle initiale.

Elle peut proposer :
- Operational Modules ;
- Operational Domains ;
- Operational Units ;
- Runtime Tags ;
- Runtime Vocabulary ;
- Routing Hints.

## 7.2 L'IA ne décide pas

Décision validée :

```txt
IA propose
Humain valide
Backend active
```

Aucune structure runtime n'est activée automatiquement sans validation humaine.

## 7.3 Flow IA

```txt
Establishment description submitted
        ↓
AI interpretation started
        ↓
Modules proposed
Domains proposed
Units proposed
Tags proposed
Vocabulary proposed
Routing hints proposed
        ↓
Human validation
        ↓
Runtime activation
```

## 7.4 Échec IA

Si l'IA échoue :

```txt
Retry possible
+
Fallback manuel
+
Templates par défaut
```

## 7.5 Onboarding manuel

Onboarding manuel possible si l'IA est indisponible.

```txt
Manual onboarding fallback = yes
```

---

# 8. Validation humaine

## 8.1 Validation obligatoire

Toutes les propositions IA doivent être validées avant activation runtime.

## 8.2 Validation par section

Validation par section :

```txt
modules
domains
units
vocabulary
routing hints
```

Chaque section peut avoir un bouton :

```txt
Accept all
```

## 8.3 Modification avant activation

Avant activation, l'utilisateur peut :

```txt
modifier
ajouter
supprimer
```

Éléments modifiables :
- modules ;
- domains ;
- units ;
- tags ;
- vocabulary.

## 8.4 Sections optionnelles

Les sections suivantes peuvent être passées :

```txt
vocabulary
tags
routing hints
```

Les sections suivantes sont obligatoires :

```txt
modules
domains
```

## 8.5 Modification post-activation

Après activation :
- Owner / Director peuvent modifier la structure ;
- certains éléments peuvent être modifiés par Manager selon permissions ;
- les changements structurants doivent être audités.

## 8.6 Versioning

Pas de versioning complet de configuration au MVP.

```txt
No full configuration versioning MVP
```

Audit simple des changements structurants recommandé.

---

# 9. Operational Modules MVP

## 9.1 Modules validés pour Mama Shelter Nice

```txt
Operational Modules MVP
├── hotel
├── restaurant
├── bar
├── rooftop
├── seminar_rooms
└── coworking
```

## 9.2 Définition

Un Operational Module représente une activité présente dans l'établissement.

## 9.3 Attention à ne pas confondre

```txt
Operational Module ≠ Operational Domain
Operational Module ≠ Operational Unit
```

Exemple :
- `restaurant` peut être un module ;
- `kitchen` peut être un domain ou une unit selon le choix produit ;
- `maintenance` est un domain.

---

# 10. Operational Domains MVP

## 10.1 Domains validés

```txt
Operational Domains MVP
├── maintenance
├── housekeeping
├── cleaning
├── security
├── guest_experience
├── kitchen
├── dinning_room
├── pricing
├── event_management
└── management
```

## 10.2 Rôle des domains

Les domains servent à :
- alimenter `detected_domains[]` des Signals ;
- configurer les feeds personnels ;
- router les notifications ;
- définir l'actionabilité manager ;
- assigner les responsabilités de supervision ;
- mesurer la qualité IA.

## 10.3 Cleaning et housekeeping

Décision validée :

```txt
cleaning et housekeeping sont deux domains séparés.
```

## 10.4 Alerte produit

`kitchen` et `restaurant_room` peuvent être interprétés comme :
- domains opérationnels ;
- équipes ;
- zones ;
- ou units.

Ils sont retenus comme domains MVP car validés, mais il faudra surveiller l'usage terrain.

Risque :
- doublon avec `Operational Units` ;
- ambiguïté entre équipe et lieu ;
- difficulté de routing si `kitchen` est à la fois domain et unit.

Recommandation :
- garder MVP tel quel ;
- mesurer les corrections de domains ;
- ajuster après pilote terrain si ambigu.

---

# 11. Operational Units MVP

## 11.1 Units validées

```txt
Operational Units MVP
├── lobby
├── rooms
├── corridors
├── restaurant
├── kitchen
├── bar
├── rooftop
├── seminar_rooms
├── storage
├── technical_rooms
└── outdoor_areas
```

## 11.2 Rôle des units

Les units servent à :
- contextualiser les Signals ;
- améliorer l'agrégation ;
- aider le routing ;
- structurer la supervision ;
- interpréter les signalements terrain.

## 11.3 Chambres

Décision validée :

```txt
Pas de création exhaustive des chambres.
```

On garde :

```txt
unit = rooms
```

Et les numéros de chambre sont détectés dans le texte.

Exemple :

```txt
"chambre 312"
→ unit rooms
→ location text: chambre 312
```

---

# 12. Runtime Vocabulary

## 12.1 Décision

Un vocabulary initial minimal est créé pendant l'onboarding.

Il sera enrichi progressivement par l'usage runtime.

```txt
Runtime Vocabulary initial minimal
+
runtime enrichment progressif
```

## 12.2 Exemples validés

```txt
roof → rooftop
la plonge → kitchen / washing area
chambre 312 → rooms
coup de feu → restaurant rush
dans le jus → restaurant rush
la carte → menu du restaurant
caisse → payment terminal / pricing / food_service selon contexte
PMS → hotel system
TPE → payment terminal
VRV → HVAC / maintenance
```

## 12.3 Rôle du vocabulary

Le vocabulary sert à :
- enrichir les prompts IA ;
- améliorer le routing ;
- améliorer l'aggregation ;
- reconnaître les termes locaux ;
- limiter les erreurs d'interprétation.

## 12.4 Vocabulary optionnel

La validation du vocabulary peut être passée pendant onboarding.

Mais il est recommandé d'en activer un minimum.

---

# 13. Runtime Tags

## 13.1 Rôle

Les runtime tags sont des labels contextuels flexibles.

Ils servent à :
- enrichir les Signals ;
- améliorer la recherche ;
- améliorer l'aggregation ;
- améliorer les analytics ;
- améliorer le routing.

## 13.2 Tags MVP

Les tags sont proposés par l'IA pendant onboarding, mais leur validation peut être passée.

## 13.3 Important

Les runtime tags ne pilotent pas les permissions.

```txt
Runtime Tags ≠ permissions
Runtime Tags ≠ operational_domains
```

---

# 14. Routing Hints

## 14.1 Décision

Routing hints générés à partir des éléments validés :

```txt
modules
domains
units
vocabulary
```

## 14.2 Rôle

Les routing hints aident le pipeline IA à proposer :
- `detected_domains[]` ;
- runtime tags ;
- aggregation candidates ;
- domain confidence scores.

## 14.3 Validation

Les routing hints sont proposés mais peuvent être passés pendant onboarding.

## 14.4 Exemple

```txt
Si texte contient "VRV", "clim", "froid", "chauffage"
→ proposer domain maintenance
```

```txt
Si texte contient "la carte", "prix", "menu", "erreur tarif"
→ proposer domain pricing
```

---

# 15. Signal examples

## 15.1 Décision

Des exemples pédagogiques de Signals peuvent être générés.

```txt
Signal examples = optional
```

## 15.2 Non requis pour activation

Ces exemples ne sont pas nécessaires pour activer l'établissement.

## 15.3 Rôle

Ils aident Owner/Director/Manager à comprendre :
- ce qu'un signalement produit ;
- comment les domains sont utilisés ;
- comment une situation devient actionnable.

---

# 16. Checklists pendant onboarding

## 16.1 Décision

Les checklists types ne font pas partie de l'activation minimale.

```txt
Checklist templates
= hors activation minimale
```

## 16.2 Pourquoi

Les Shared Checklists sont MVP, mais leur création/configuration doit être traitée dans le Checklist Domain.

Ne pas mélanger :
- activation établissement ;
- configuration des routines.

## 16.3 Après activation

Des templates checklist pourront être proposés après activation ou dans une checklist de configuration progressive.

---

# 17. Users / Memberships

## 17.1 Règle

Onboarding demande au moins les managers/directors initiaux.

Pas besoin de l'organigramme complet.

## 17.2 Invitation minimum

```txt
Onboarding invite au minimum 1 Director ou Manager.
```

## 17.3 Staff

Staff invitations possibles après activation.

## 17.4 Roles pendant onboarding

```txt
Owner
Director
Manager
```

## 17.5 Domains sur memberships

Pendant onboarding, assigner les operational_domains au minimum aux managers initiaux.

```txt
Manager
├── role
└── operational_domains[]
```

Owner / Director voient tout, mais leurs memberships existent quand même.

## 17.6 Membership activation

Un user invité devient opérationnel quand :
- invitation acceptée ;
- membership actif ;
- role défini ;
- establishment rattaché ;
- operational_domains assignés si Manager.

---

# 18. Résumé avant activation

## 18.1 Décision

Un écran résumé minimal est obligatoire avant activation.

## 18.2 Contenu résumé

```txt
Activation Summary
├── Organization
├── Establishment
├── Description
├── Modules validés
├── Domains validés
├── Units validées
├── Vocabulary activé
├── Managers / Directors initiaux
└── Readiness status
```

## 18.3 Objectif

L'écran résumé sert à :
- éviter une activation accidentelle ;
- confirmer les domains ;
- vérifier les managers ;
- confirmer que le runtime minimal est prêt.

---

# 19. Activation établissement

## 19.1 Critères d'activation minimum

```txt
Activation minimum
├── Organization créée
├── Establishment créé
├── description établissement validée
├── au moins 1 module validé
├── au moins 3 domains validés
├── au moins 1 Owner ou Director actif
├── au moins 1 Manager actif ou invité
└── operational_domains assignés aux managers initiaux
```

## 19.2 Activation

Quand les critères sont remplis :

```txt
EstablishmentActivated
```

## 19.3 Après activation

Après activation :

```txt
Accès app
+
checklist de configuration progressive
```

---

# 20. Onboarding progressif

## 20.1 Décision

Onboarding progressif via suggestions runtime après usage terrain.

## 20.2 Sources de suggestions

Les suggestions peuvent venir :
- des Observations ;
- des corrections managers ;
- des Signals ;
- des domains ajoutés/retirés ;
- des terms récurrents ;
- des routing corrections ;
- des checklists créées.

## 20.3 Types de suggestions

```txt
Runtime suggestions
├── nouveau vocabulary alias
├── nouveau routing hint
├── nouvelle operational unit
├── domain correction pattern
└── checklist template suggestion post-MVP
```

## 20.4 Validation

Les suggestions runtime nécessitent validation humaine avant activation.

---

# 21. Relance IA post-activation

## 21.1 Décision

Owner/Director peuvent relancer l'IA post-activation.

## 21.2 Validation obligatoire

Même après relance :

```txt
AI proposes
Human validates
Backend activates
```

## 21.3 Cas d'usage

Relancer l'IA si :
- description établissement évolue ;
- nouveaux modules ajoutés ;
- routing faible ;
- établissement ajoute une activité ;
- contexte initial insuffisant.

---

# 22. Modèle de données recommandé

## 22.1 organizations

```txt
organizations
├── id UUID
├── name
├── created_at
└── updated_at
```

## 22.2 establishments

```txt
establishments
├── id UUID
├── organization_id UUID
├── name
├── activity_description text
├── onboarding_status enum
│   ├── not_started
│   ├── in_progress
│   ├── ready_for_activation
│   └── activated
├── activated_at datetime nullable
├── created_at
└── updated_at
```

## 22.3 onboarding_sessions

```txt
onboarding_sessions
├── id UUID
├── organization_id UUID
├── establishment_id UUID
├── started_by_id UUID
├── status enum
│   ├── started
│   ├── ai_processing
│   ├── awaiting_validation
│   ├── ready_for_activation
│   ├── activated
│   └── failed
├── ai_attempts integer
├── last_error_code nullable
├── last_error_message nullable
├── created_at
└── updated_at
```

## 22.4 operational_modules

```txt
operational_modules
├── id UUID
├── establishment_id UUID
├── key string
├── label string
├── source enum
│   ├── ai_proposed
│   ├── manual
│   └── template
├── active boolean
├── created_at
└── updated_at
```

## 22.5 operational_domains

```txt
operational_domains
├── id UUID
├── establishment_id UUID
├── key string
├── label string
├── source enum
│   ├── ai_proposed
│   ├── manual
│   └── template
├── active boolean
├── created_at
└── updated_at
```

## 22.6 operational_units

```txt
operational_units
├── id UUID
├── establishment_id UUID
├── key string
├── label string
├── source enum
│   ├── ai_proposed
│   ├── manual
│   └── template
├── active boolean
├── created_at
└── updated_at
```

## 22.7 runtime_vocabulary_entries

```txt
runtime_vocabulary_entries
├── id UUID
├── establishment_id UUID
├── term string
├── meaning string
├── mapped_domain nullable
├── mapped_unit nullable
├── source enum
│   ├── ai_proposed
│   ├── manual
│   ├── runtime_suggestion
│   └── template
├── active boolean
├── created_at
└── updated_at
```

## 22.8 routing_hints

```txt
routing_hints
├── id UUID
├── establishment_id UUID
├── pattern string
├── suggested_domain string
├── suggested_tags jsonb
├── confidence numeric nullable
├── source enum
│   ├── ai_proposed
│   ├── manual
│   ├── runtime_suggestion
│   └── template
├── active boolean
├── created_at
└── updated_at
```

---

# 23. Events Onboarding MVP

## 23.1 Events validés

```txt
OrganizationCreated
EstablishmentCreated
OnboardingStarted
EstablishmentDescriptionSubmitted
OnboardingAIInterpretationStarted
OnboardingAIInterpretationSucceeded
OnboardingAIInterpretationFailed
OperationalModulesProposed
OperationalDomainsProposed
OperationalUnitsProposed
RuntimeVocabularyProposed
OnboardingProposalValidated
OperationalModuleActivated
OperationalDomainActivated
OperationalUnitActivated
RuntimeVocabularyActivated
EstablishmentActivated
InitialUserInvited
MembershipActivated
```

## 23.2 Payload minimal recommandé

### OrganizationCreated

```json
{
  "event_type": "OrganizationCreated",
  "organization_id": "uuid",
  "name": "Mama Shelter",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### EstablishmentCreated

```json
{
  "event_type": "EstablishmentCreated",
  "organization_id": "uuid",
  "establishment_id": "uuid",
  "name": "Mama Shelter Nice",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### OnboardingStarted

```json
{
  "event_type": "OnboardingStarted",
  "onboarding_session_id": "uuid",
  "establishment_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### EstablishmentDescriptionSubmitted

```json
{
  "event_type": "EstablishmentDescriptionSubmitted",
  "onboarding_session_id": "uuid",
  "establishment_id": "uuid",
  "description_length": 248,
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### OnboardingAIInterpretationSucceeded

```json
{
  "event_type": "OnboardingAIInterpretationSucceeded",
  "onboarding_session_id": "uuid",
  "establishment_id": "uuid",
  "modules_count": 6,
  "domains_count": 10,
  "units_count": 11,
  "vocabulary_count": 9,
  "created_at": "datetime"
}
```

### OnboardingProposalValidated

```json
{
  "event_type": "OnboardingProposalValidated",
  "onboarding_session_id": "uuid",
  "establishment_id": "uuid",
  "section": "domains",
  "validated_count": 10,
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### EstablishmentActivated

```json
{
  "event_type": "EstablishmentActivated",
  "establishment_id": "uuid",
  "organization_id": "uuid",
  "actor_id": "uuid",
  "activated_at": "datetime"
}
```

---

# 24. API endpoints MVP

## 24.1 Start onboarding

```txt
POST /api/v1/onboarding/start
```

## 24.2 Submit organization / establishment

```txt
POST /api/v1/onboarding/organization_establishment
```

## 24.3 Submit establishment description

```txt
POST /api/v1/onboarding/establishment_description
```

## 24.4 Run AI interpretation

```txt
POST /api/v1/onboarding/:id/run_ai_interpretation
```

## 24.5 Get proposals

```txt
GET /api/v1/onboarding/:id/proposals
```

## 24.6 Validate proposal section

```txt
POST /api/v1/onboarding/:id/validate_section
```

Body example:

```json
{
  "section": "domains",
  "items": [
    { "key": "maintenance", "label": "Maintenance", "active": true },
    { "key": "pricing", "label": "Pricing", "active": true }
  ]
}
```

## 24.7 Invite initial user

```txt
POST /api/v1/onboarding/:id/invite_user
```

## 24.8 Activation summary

```txt
GET /api/v1/onboarding/:id/activation_summary
```

## 24.9 Activate establishment

```txt
POST /api/v1/onboarding/:id/activate
```

## 24.10 Rerun AI post-activation

```txt
POST /api/v1/establishments/:id/rerun_onboarding_ai
```

Owner/Director only.

---

# 25. Frontend UX

## 25.1 Onboarding steps

```txt
Step 1 — Organization & Establishment
Step 2 — Establishment description
Step 3 — AI interpretation
Step 4 — Validate modules
Step 5 — Validate domains
Step 6 — Validate units
Step 7 — Validate vocabulary / routing hints
Step 8 — Invite initial Director/Manager
Step 9 — Activation summary
Step 10 — Activate establishment
```

## 25.2 UX principles

- réduire la friction ;
- proposer des exemples ;
- permettre accept all ;
- permettre modification manuelle ;
- rendre l'IA non bloquante ;
- afficher un résumé clair ;
- ne pas demander toute l'organisation.

## 25.3 Post-activation

Après activation, afficher une checklist de configuration progressive :

```txt
Post-activation checklist
├── inviter staff
├── créer première Shared Checklist
├── tester +Signaler
├── vérifier domains managers
├── compléter vocabulary
└── lancer premier signalement terrain
```

---

# 26. Edge cases

## 26.1 Description trop courte

```txt
description < 50 caractères
→ bloquer
→ afficher exemples guidés
```

## 26.2 IA échoue

```txt
AI failed
→ retry
→ fallback manuel
→ templates par défaut
```

## 26.3 Aucun module détecté

```txt
No modules proposed
→ proposer templates défaut
→ ajout manuel obligatoire
```

## 26.4 Aucun domain validé

```txt
activation impossible
→ au moins 3 domains requis
```

## 26.5 Manager sans domain

```txt
activation impossible si aucun manager initial n'a operational_domains
```

## 26.6 Owner/Director sans Manager

```txt
activation impossible
→ au moins 1 Manager actif ou invité requis
```

## 26.7 Vocabulary ignoré

```txt
allowed
```

## 26.8 Routing hints ignorés

```txt
allowed
```

## 26.9 Staff non invités

```txt
allowed
```

Staff peuvent être invités après activation.

---

# 27. Tests fonctionnels MVP

## 27.1 Create Organization then Establishment

```txt
Given onboarding actor
When organization and establishment data are submitted
Then Organization is created
And Establishment is created under Organization
```

## 27.2 Reject establishment without organization

```txt
Given establishment creation request
When no organization exists
Then request is rejected
```

## 27.3 Description minimum

```txt
Given establishment description shorter than 50 chars
When submitted
Then request is rejected
```

## 27.4 AI proposals generated

```txt
Given valid description
When AI interpretation succeeds
Then modules/domains/units/vocabulary/routing_hints are proposed
```

## 27.5 AI failure fallback

```txt
Given AI interpretation fails
When user chooses manual fallback
Then user can manually add modules/domains/units
```

## 27.6 Human validation required

```txt
Given AI proposals exist
When user tries to activate without validation
Then activation is rejected
```

## 27.7 Activation minimum

```txt
Given Organization, Establishment, description, 1 module, 3 domains, Owner/Director, Manager and manager domains
When user activates
Then EstablishmentActivated is emitted
```

## 27.8 Activation blocked without manager domain

```txt
Given Manager invited without operational_domains
When activation requested
Then activation is rejected
```

## 27.9 Vocabulary can be skipped

```txt
Given modules/domains validated
And vocabulary skipped
When other activation criteria are met
Then activation is allowed
```

## 27.10 Rerun AI post-activation

```txt
Given activated Establishment
And Owner/Director
When rerun AI is requested
Then new proposals are generated
And human validation is required before activation
```

---

# 28. Décisions validées — index

| Décision | Statut |
|---|---:|
| Onboarding initialise un établissement utilisable rapidement | Validé |
| Contexte runtime minimal validé humainement | Validé |
| MVP pilote = Houston admin + Owner/Director | Validé |
| Produit cible = Owner ou Director | Validé |
| Organization puis Establishment | Validé |
| Establishment belongs_to Organization | Validé |
| Required MVP fields validés | Validé |
| Description libre obligatoire | Validé |
| Minimum 50 caractères | Validé |
| Exemples guidés | Validé |
| IA propose modules/domains/units/tags/vocabulary/routing hints | Validé |
| IA ne valide jamais seule | Validé |
| Validation humaine obligatoire | Validé |
| Validation par section | Validé |
| Accept all par section | Validé |
| Modification/suppression/ajout manuel avant activation | Validé |
| Vocabulary/tags/routing hints peuvent être passés | Validé |
| Modules/domains minimum obligatoires | Validé |
| Structure modifiable post-activation | Validé |
| Retry IA + fallback manuel + templates défaut | Validé |
| Onboarding manuel possible | Validé |
| Modules MVP validés | Validé |
| Domains MVP validés | Validé |
| Cleaning et housekeeping séparés | Validé |
| Units MVP validées | Validé |
| Pas de création exhaustive des chambres | Validé |
| Runtime vocabulary initial minimal | Validé |
| Routing hints générés | Validé |
| Exemples Signals optionnels | Validé |
| Checklists types hors activation minimale | Validé |
| Managers/Directors initiaux demandés | Validé |
| Staff après activation | Validé |
| Domains assignés aux managers initiaux | Validé |
| Écran résumé avant activation | Validé |
| Activation minimum validé | Validé |
| Accès app + checklist progressive après activation | Validé |
| Onboarding progressif runtime | Validé |
| Relance IA post-activation Owner/Director | Validé |
| Pas de versioning complet MVP | Validé |
| Events Onboarding MVP validés | Validé |

---

# 30. Recommandation finale

Le domaine Onboarding est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Onboarding = bootstrap rapide d'un établissement,
pas modélisation complète de l'organisation.
```

Le build doit maintenant s'appuyer sur :
- Organization puis Establishment ;
- description libre guidée ;
- IA de proposition ;
- validation humaine obligatoire ;
- sections modifiables ;
- activation minimale stricte ;
- users initiaux avec domains ;
- fallback manuel ;
- onboarding progressif après activation.

La prochaine étape logique est le **Checklist Domain**, car les checklists sont dans le MVP mais leur lifecycle détaillé reste à documenter.
