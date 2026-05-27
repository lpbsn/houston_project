# Houston — AI Onboarding Contract

**Version:** v0.1  
**Date:** 2026-05-23  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — AI Onboarding → runtime proposals  
**Documents liés:**  
- `Houston_ai_overview.md`
- `Houston_onboarding_domain.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_ai_transcription_contract.md`
- `Houston_rbac_permissions_domain.md`

---

# 1. Objectif du document

Ce document formalise le contrat **AI Onboarding** de Houston.

Il définit :
- le rôle de l’IA Onboarding ;
- les inputs envoyés à l’IA ;
- les données exclues ;
- les outputs attendus ;
- le JSON schema cible ;
- les règles de validation backend ;
- les règles de validation humaine ;
- les limites par section ;
- les fallbacks ;
- les retries / timeouts ;
- les events ;
- les metrics ;
- les tests fonctionnels attendus.

Ce document ne couvre pas :
- la création réelle des rôles et permissions ;
- la facturation ;
- la création de ChecklistTemplates ;
- l’analyse des Observations terrain ;
- la transcription audio.

---

# 2. Principe central

```txt
AI bootstraps.
Human validates.
Backend activates.
```

En français :

```txt
L’IA prépare une structure initiale.
L’humain valide.
Le backend active.
```

---

# 3. Rôle de l’AI Onboarding

## 3.1 Définition

AI Onboarding analyse la description d’un établissement et propose une structure runtime initiale validable humainement.

```txt
Establishment description
        ↓
AI Onboarding
        ↓
Runtime proposals
        ↓
Human validation
        ↓
Backend activation
```

## 3.2 Ce que l’IA peut proposer

L’IA peut proposer :
- operational modules ;
- operational domains ;
- operational units ;
- runtime vocabulary ;
- runtime tags ;
- routing hints.

## 3.3 Ce que l’IA ne fait pas

L’IA ne :
- n’active jamais directement un élément runtime ;
- ne modifie jamais directement la base ;
- ne crée pas d’Organization ;
- ne crée pas d’Establishment ;
- ne crée pas de rôles ;
- ne crée pas de permissions ;
- ne crée pas d’assignments utilisateurs ;
- ne crée pas de ChecklistTemplates au MVP ;
- ne produit pas de Signal examples au MVP ;
- ne produit pas de billing/subscription/pricing produit ;
- ne décide pas de l’activation finale.

---

# 4. Workflow global

## 4.1 Flow standard

```txt
Organization / Establishment data submitted
        ↓
Establishment activity description submitted
        ↓
AI Onboarding interpretation started
        ↓
AI returns structured proposals
        ↓
Backend validates output
        ↓
User reviews by section
        ↓
User edits / accepts / removes proposals
        ↓
Backend activates validated structure
        ↓
Establishment activation possible if minimum criteria met
```

## 4.2 Flow en cas d’échec IA

```txt
AI failure
        ↓
Retry if attempts remain
        ↓
OnboardingAIInterpretationFailed
        ↓
Manual fallback
        ↓
Default templates
```

## 4.3 Flow post-activation

```txt
Owner/Director reruns AI
        ↓
New proposals generated
        ↓
Human review required
        ↓
Backend applies only validated changes
```

Aucune mutation automatique post-activation.

---

# 5. Input contract

## 5.1 Input général

```txt
Input IA Onboarding
├── organization_name
├── establishment_name
├── establishment_activity_description
├── allowed_module_catalog
├── allowed_domain_catalog
├── allowed_unit_catalog
├── locale
└── prompt_version
```

## 5.2 Payload recommandé

```json
{
  "organization_name": "Mama Shelter",
  "establishment_name": "Mama Shelter Nice",
  "establishment_activity_description": "Hôtel avec restaurant, bar, rooftop, salles de séminaire et coworking.",
  "allowed_module_catalog": [],
  "allowed_domain_catalog": [],
  "allowed_unit_catalog": [],
  "locale": "fr-FR",
  "prompt_version": "ai_onboarding_v1"
}
```

## 5.3 Données exclues

Ne pas envoyer :
- données utilisateurs nominatives ;
- emails ;
- numéros de téléphone ;
- assignments utilisateurs ;
- rôles nominatifs ;
- adresse/localisation exacte au MVP ;
- données billing ;
- données subscription ;
- historique complet d’usage ;
- Observations ;
- Signals ;
- Actions.

---

# 6. Output contract

## 6.1 Outputs attendus

```txt
AI Onboarding outputs
├── operational_modules
├── operational_domains
├── operational_units
├── runtime_vocabulary
├── runtime_tags
└── routing_hints
```

## 6.2 Outputs exclus MVP

L’IA Onboarding ne produit pas :
- ChecklistTemplates ;
- Signal examples ;
- roles ;
- permissions ;
- user assignments ;
- billing ;
- subscription ;
- product pricing.

---

# 7. Outcomes

## 7.1 Outcomes possibles

```txt
proposal_generated
insufficient_input
invalid_input
```

## 7.2 proposal_generated

Utilisé quand l’IA produit une proposition structurée exploitable.

## 7.3 insufficient_input

Utilisé quand la description établissement est trop pauvre pour produire une proposition fiable.

Backend / UX :

```txt
Demander enrichissement description
OU
fallback manuel/templates
```

## 7.4 invalid_input

Utilisé quand l’input ne respecte pas le contrat attendu.

Backend :
- retry si pertinent ;
- sinon failed ;
- fallback manuel/templates.

---

# 8. JSON schema global

## 8.1 Structure globale

```json
{
  "schema_version": "ai_onboarding_output_v1",
  "outcome": "proposal_generated",
  "operational_modules": [],
  "operational_domains": [],
  "operational_units": [],
  "runtime_vocabulary": [],
  "runtime_tags": [],
  "routing_hints": []
}
```

## 8.2 Règles générales

Le JSON doit :
- être parseable ;
- respecter `schema_version` ;
- contenir un `outcome` autorisé ;
- séparer clairement les sections ;
- respecter les caps par section ;
- utiliser des keys stables issues des catalogues pour modules/domains/units ;
- fournir une `reason` courte pour chaque proposition ;
- fournir un `confidence_score` techniquement requis sur les items concernés.

---

# 9. Operational modules

## 9.1 Champs requis

```txt
OperationalModule proposal
├── key
├── label
├── reason
└── confidence_score
```

## 9.2 Catalogue autorisé

L’IA doit choisir uniquement dans :

```txt
allowed_module_catalog
```

## 9.3 Module inconnu

Si l’IA propose un module inconnu :

```txt
Module inconnu supprimé.
Warning technique.
```

## 9.4 Cap MVP

```txt
modules max 10
```

---

# 10. Operational domains

## 10.1 Champs requis

```txt
OperationalDomain proposal
├── key
├── label
├── reason
├── confidence_score
└── related_modules[]
```

## 10.2 Catalogue autorisé

L’IA doit choisir uniquement dans :

```txt
allowed_domain_catalog
```

## 10.3 Domain inconnu

Si l’IA propose un domain inconnu :

```txt
Domain inconnu supprimé.
```

Si aucun domain valide n’est proposé :

```txt
output technique invalide
OU
fallback template
```

## 10.4 Minimum requis

L’AI output doit proposer au moins :

```txt
3 operational_domains valides
```

## 10.5 Maximum MVP

```txt
domains max 15
```

---

# 11. Operational units

## 11.1 Champs requis

```txt
OperationalUnit proposal
├── key
├── label
├── reason
├── confidence_score
└── related_modules[]
```

## 11.2 Catalogue autorisé

MVP :

```txt
units issues du allowed_unit_catalog
```

## 11.3 Suggestions libres

Suggestions libres éventuelles :
- ignorées ;
- ou stockées comme notes techniques.

Elles ne sont pas activées automatiquement.

## 11.4 Chambres individuelles

AI Onboarding ne crée pas chaque chambre.

```txt
No individual room creation.
```

Exemple :

```txt
rooms = unit
"chambre 312" = location_text runtime later
```

## 11.5 Cap MVP

```txt
units max 15
```

---

# 12. Runtime vocabulary

## 12.1 Champs requis

```txt
RuntimeVocabulary proposal
├── term
├── meaning
├── mapped_domain optional
├── mapped_unit optional
└── reason
```

## 12.2 mapped_domain

`mapped_domain` doit appartenir aux domains autorisés/proposés validement.

Sinon :

```txt
mapped_domain = null
```

## 12.3 mapped_unit

`mapped_unit` doit appartenir aux units autorisées/proposées validement.

Sinon :

```txt
mapped_unit = null
```

## 12.4 Cap MVP

```txt
vocabulary max 30
```

---

# 13. Runtime tags

## 13.1 Champs requis

```txt
RuntimeTag proposal
├── key
├── label
├── reason
└── related_domains[]
```

## 13.2 Permissions

Les runtime tags ne pilotent jamais les permissions.

```txt
Runtime tags ≠ permissions
```

## 13.3 Cap MVP

```txt
runtime_tags max 30
```

---

# 14. Routing hints

## 14.1 Champs requis

```txt
RoutingHint proposal
├── pattern
├── suggested_domains[]
├── suggested_unit optional
├── reason
└── confidence_score
```

## 14.2 Multi-domain

Un routing hint peut proposer plusieurs `suggested_domains`.

Limite :

```txt
max suggested_domains = 4
```

## 14.3 Validation

Chaque `suggested_domain` doit appartenir aux domains autorisés/proposés validement.  
`suggested_unit` doit appartenir aux units autorisées/proposées validement ou être null.

## 14.4 Cap MVP

```txt
routing_hints max 30
```

---

# 15. Confidence score et reason

## 15.1 confidence_score

`confidence_score` est requis techniquement.

Affichage UI :

```txt
optionnel, pas central
```

Usage :
- tri ;
- debug ;
- analyse qualité ;
- comparaison prompts/providers.

## 15.2 reason courte

Chaque proposition doit avoir une `reason` courte.

Objectif :
- aider l’humain à valider ;
- expliquer brièvement pourquoi l’élément est proposé.

Format :

```txt
1 phrase courte.
Pas de long raisonnement.
```

---

# 16. Caps MVP

```txt
Caps recommandés MVP
├── modules max 10
├── domains max 15
├── units max 15
├── vocabulary max 30
├── routing_hints max 30
└── runtime_tags max 30
```

Pourquoi :
- éviter onboarding trop long ;
- réduire surcharge cognitive ;
- maîtriser coût et volume IA ;
- accélérer validation humaine.

---

# 17. Keys et labels

## 17.1 Key stable

```txt
key stable issue du catalogue.
```

## 17.2 Label modifiable

```txt
label modifiable humainement.
```

Backend utilise `key`.  
L’humain peut adapter `label`.

---

# 18. Validation backend

## 18.1 Stages

```txt
AI output
        ↓
JSON parse validation
        ↓
schema validation
        ↓
catalog validation
        ↓
caps validation
        ↓
minimum proposal validation
        ↓
human review
```

## 18.2 Catalog validation

Vérifier :
- module keys autorisées ;
- domain keys autorisées ;
- unit keys autorisées ;
- mapped_domain valide ou null ;
- mapped_unit valide ou null ;
- routing suggested_domains valides ;
- routing suggested_unit valide ou null.

## 18.3 Unknown values

Unknown values are removed or ignored.

Ne jamais créer automatiquement :
- module inconnu ;
- domain inconnu ;
- unit inconnue.

## 18.4 Minimum domains

Si moins de 3 valid domains :

```txt
fallback template
OU
output invalid
```

---

# 19. Validation humaine

## 19.1 Validation obligatoire

Toute proposition IA doit être validée humainement avant activation runtime.

## 19.2 Sections éditables

Avant activation, l’utilisateur peut éditer :

```txt
modules
domains
units
tags
vocabulary
routing hints
```

## 19.3 Validation par section

```txt
Validation par section + accept all par section.
```

## 19.4 Sections skippables

```txt
Skippable:
├── runtime_vocabulary
├── runtime_tags
└── routing_hints
```

## 19.5 Sections required

```txt
Required:
├── operational_modules
└── operational_domains
```

---

# 20. Activation minimum

```txt
Activation minimum
├── Organization créée
├── Establishment créé
├── description validée
├── au moins 1 module validé
├── au moins 3 domains validés
├── au moins 1 Owner ou Director actif
├── au moins 1 Manager actif ou invité
└── operational_domains assignés aux managers initiaux
```

Même si l’IA propose une structure correcte, l’établissement n’est activable que si tous les critères backend sont remplis.

---

# 21. Invalid JSON / failure

## 21.1 Invalid JSON

```txt
Invalid JSON
        ↓
retry limité
        ↓
OnboardingAIInterpretationFailed
        ↓
fallback manuel/templates
```

## 21.2 Max attempts

```txt
max_attempts = 3
```

## 21.3 Timeout

```txt
timeout = 60s
```

## 21.4 AI failure

```txt
AI failure
→ retry possible
→ manual fallback
→ default templates
```

---

# 22. Default templates

## 22.1 Décision

Default templates par module ou secteur d’activité.

## 22.2 Rôle

Ils permettent de continuer l’onboarding si :
- IA échoue ;
- input insuffisant ;
- output invalide ;
- provider indisponible.

Exemples :
- hotel → maintenance, housekeeping, guest_experience, security, management ;
- restaurant → kitchen, dining_room, cleaning, pricing, management ;
- rooftop/bar → security, dining_room, pricing, cleaning, management.

---

# 23. Rerun AI post-activation

## 23.1 Qui peut relancer

```txt
Owner
Director
```

## 23.2 Validation humaine

Rerun post-activation nécessite validation humaine obligatoire.

## 23.3 No direct mutation

```txt
Post-activation AI rerun = new proposals only.
No direct mutation.
```

## 23.4 Suppressions proposées

Suppressions post-activation :

```txt
suggestions de review
jamais auto-appliquées
```

Pourquoi :
- des Signals/Actions peuvent dépendre d’un domain ;
- des managers peuvent avoir des operational_domains ;
- des metrics peuvent dépendre d’une structure ;
- suppression automatique dangereuse.

---

# 24. Storage and logs

## 24.1 Output structuré

Stocker output structuré temporairement :

```txt
retention = 14 jours
```

## 24.2 Prompts

```txt
Pas de prompt complet en logs.
```

## 24.3 AIUsageLog

Chaque AI Onboarding call crée un AIUsageLog :

```txt
ai_domain = onboarding
```

Champs :

```txt
AIUsageLog
├── establishment_id
├── ai_domain=onboarding
├── provider
├── model
├── prompt_version
├── status
├── latency_ms
├── input_tokens
├── output_tokens
├── cost_estimate
├── error_code
├── correlation_id
└── created_at
```

---

# 25. Events

## 25.1 Events validés

```txt
AIRequestStarted
AIRequestSucceeded
AIRequestFailed
AIRequestRetried
OnboardingAIInterpretationStarted
OnboardingAIInterpretationSucceeded
OnboardingAIInterpretationFailed
OperationalModulesProposed
OperationalDomainsProposed
OperationalUnitsProposed
RuntimeVocabularyProposed
OnboardingProposalValidated
RuntimeTagsProposed
RoutingHintsProposed
```

## 25.2 Events d’activation hors contrat IA

Les events d’activation réelle restent dans Onboarding Domain :

```txt
OperationalModuleActivated
OperationalDomainActivated
OperationalUnitActivated
RuntimeVocabularyActivated
EstablishmentActivated
InitialUserInvited
MembershipActivated
```

## 25.3 Event correlation

Tous les events doivent porter :
- correlation_id ;
- onboarding_session_id ;
- establishment_id si disponible ;
- actor_id si action humaine.

---

# 26. UX states

```txt
ai_interpretation_pending
ai_interpretation_processing
ai_interpretation_ready
ai_interpretation_failed
```

## 26.1 ai_interpretation_pending

La demande n’a pas encore démarré.

## 26.2 ai_interpretation_processing

L’IA interprète la description.

## 26.3 ai_interpretation_ready

Les propositions sont prêtes à être relues.

## 26.4 ai_interpretation_failed

L’IA a échoué.

UX :
- retry ;
- fallback manuel ;
- templates par défaut.

---

# 27. Metrics MVP

## 27.1 Metrics AI Onboarding

```txt
proposed modules count
accepted modules count
rejected modules count
accepted domains count
rejected domains count
manual additions count
manual edits count
AI failure rate
latency
cost per onboarding
```

## 27.2 Corrections post-activation à suivre

```txt
domains ajoutés post-activation
domains retirés post-activation
units ajoutées post-activation
vocabulary ajouté post-activation
routing corrections
```

## 27.3 Pourquoi

Ces metrics mesurent :
- qualité du bootstrap IA ;
- utilité réelle de l’IA ;
- dette de configuration ;
- effort humain de correction ;
- coût ;
- performance.

---

# 28. API endpoints MVP

## 28.1 Start AI interpretation

```txt
POST /api/v1/onboarding/:id/ai_interpretation
```

## 28.2 Get AI proposals

```txt
GET /api/v1/onboarding/:id/ai_proposals
```

## 28.3 Validate section

```txt
POST /api/v1/onboarding/:id/validate_section
```

## 28.4 Retry AI interpretation

```txt
POST /api/v1/onboarding/:id/retry_ai_interpretation
```

## 28.5 Rerun post-activation

```txt
POST /api/v1/establishments/:id/onboarding_ai_rerun
```

Owner/Director only.

---

# 29. Backend services recommandés

## 29.1 Ai::Onboarding::BuildInput

Responsabilités :
- collecter organization_name ;
- collecter establishment_name ;
- collecter description ;
- injecter allowed catalogs ;
- définir locale ;
- définir prompt_version ;
- minimiser les données.

## 29.2 Ai::Onboarding::InterpretEstablishment

Responsabilités :
- call provider ;
- enforce timeout 60s ;
- log AIUsageLog ;
- return structured output.

## 29.3 Ai::Onboarding::ValidateOutput

Responsabilités :
- parse JSON ;
- valider schema ;
- supprimer unknown modules/domains/units ;
- appliquer caps ;
- valider minimum domains ;
- produire proposal nettoyée.

## 29.4 Onboarding::StoreAIProposal

Responsabilités :
- stocker output structuré temporairement ;
- créer sections relisibles ;
- préparer validation humaine.

## 29.5 Onboarding::ValidateProposalSection

Responsabilités :
- accepter / éditer / supprimer items ;
- tracer actor ;
- émettre OnboardingProposalValidated.

## 29.6 Onboarding::ActivateValidatedStructure

Responsabilités :
- vérifier activation minimum ;
- activer modules/domains/units/vocabulary validés ;
- émettre events d’activation.

---

# 30. Data model recommandé

## 30.1 onboarding_ai_proposals

```txt
onboarding_ai_proposals
├── id UUID
├── onboarding_session_id UUID
├── establishment_id UUID nullable
├── ai_usage_log_id UUID
├── schema_version string
├── outcome string
├── sanitized_output_json jsonb
├── status enum
│   ├── pending
│   ├── ready_for_review
│   ├── partially_validated
│   ├── validated
│   └── failed
├── expires_at datetime
├── created_at
└── updated_at
```

## 30.2 onboarding_proposal_items

Optionnel si on veut gérer item par item.

```txt
onboarding_proposal_items
├── id UUID
├── onboarding_ai_proposal_id UUID
├── section string
├── key string nullable
├── label string nullable
├── payload jsonb
├── status enum
│   ├── proposed
│   ├── accepted
│   ├── edited
│   ├── rejected
│   └── skipped
├── actor_id UUID nullable
├── created_at
└── updated_at
```

---

# 31. Edge cases

## 31.1 Description trop pauvre

```txt
outcome = insufficient_input
UX asks richer description or fallback manual/templates
```

## 31.2 AI returns unknown module

Remove unknown module.

## 31.3 AI returns unknown domain

Remove unknown domain.

If no valid domain remains :
- invalid output ;
- fallback template.

## 31.4 AI returns unknown unit

Remove unknown unit or store as technical note.

## 31.5 AI returns too many items

Apply caps.

## 31.6 AI returns roles/permissions

Ignore and log warning.

## 31.7 AI returns ChecklistTemplates

Ignore and log warning.

## 31.8 AI returns billing/pricing product

Ignore and log warning.

## 31.9 Rerun proposes removing a used domain

Never auto-remove.  
Create review suggestion only.

## 31.10 User skips vocabulary/tags/routing hints

Allowed.

## 31.11 User skips modules/domains

Not allowed for activation.

---

# 32. Tests fonctionnels MVP

## 32.1 Valid AI proposal generated

```txt
Given valid establishment description
When AI onboarding runs
Then proposal_generated output is stored
And sections are available for human review
```

## 32.2 Unknown module removed

```txt
Given AI returns module not in allowed_module_catalog
When backend validates output
Then module is removed
And warning is logged
```

## 32.3 Unknown domain removed

```txt
Given AI returns domain not in allowed_domain_catalog
When backend validates output
Then domain is removed
```

## 32.4 No valid domains

```txt
Given AI returns no valid domain
When backend validates output
Then proposal is invalid
And fallback templates are offered
```

## 32.5 Caps applied

```txt
Given AI returns 20 domains
When backend validates output
Then only max 15 domains are kept
```

## 32.6 Invalid JSON retry

```txt
Given provider returns invalid JSON
When AI onboarding runs
Then retry is attempted until max_attempts
And failure falls back to manual/templates
```

## 32.7 Human validation required

```txt
Given AI proposals are ready
When user tries to activate without validating required sections
Then activation is rejected
```

## 32.8 Sections editable

```txt
Given proposal item label
When user edits label
Then edited label is stored
And key remains stable
```

## 32.9 Skippable sections

```txt
Given user skips runtime_vocabulary
When required modules/domains are validated
Then activation can still proceed if activation minimum is met
```

## 32.10 No direct mutation

```txt
Given AI output contains valid modules/domains
When AI interpretation succeeds
Then runtime modules/domains are not activated until human validation
```

## 32.11 Rerun post-activation

```txt
Given activated establishment
And Owner/Director reruns AI
When new proposals are generated
Then no structure is mutated automatically
```

---

# 33. Décisions validées — index

| Décision | Statut |
|---|---:|
| AI Onboarding propose structure runtime initiale | Validé |
| IA n’active jamais directement | Validé |
| Humain valide | Validé |
| Backend active | Validé |
| Input contract validé | Validé |
| Aucune donnée utilisateur nominative envoyée | Validé |
| Adresse/localisation exacte non requise MVP | Validé |
| Outputs modules/domains/units/vocabulary/tags/routing_hints | Validé |
| Pas de ChecklistTemplates MVP | Validé |
| Pas de Signal examples MVP | Validé |
| Outcomes proposal_generated/insufficient_input/invalid_input | Validé |
| JSON strict avec sections séparées | Validé |
| Modules from allowed catalog only | Validé |
| Unknown modules removed | Validé |
| Domains from allowed catalog only | Validé |
| Unknown domains removed | Validé |
| Minimum 3 valid domains | Validé |
| Max 15 domains | Validé |
| Units from allowed catalog | Validé |
| No individual rooms creation | Validé |
| mapped_domain valid or null | Validé |
| Runtime tags no permissions | Validé |
| Routing hints multi-domain max 4 | Validé |
| confidence_score technically required | Validé |
| Short reason per proposal | Validé |
| Caps MVP validés | Validé |
| Stable key from catalog | Validé |
| Human-editable label | Validé |
| Invalid JSON retry then failed/fallback | Validé |
| max_attempts 3 | Validé |
| timeout 60s | Validé |
| AI failure fallback manual/templates | Validé |
| Default templates by module/sector | Validé |
| Rerun post-activation Owner/Director | Validé |
| Rerun proposals only, no mutation | Validé |
| Post-activation removals review only | Validé |
| Structured output retained 14 days | Validé |
| AIUsageLog onboarding required | Validé |
| Events validés | Validé |
| RuntimeTagsProposed and RoutingHintsProposed added | Validé |
| UX states validés | Validé |
| Sections editable before activation | Validé |
| Validation by section + accept all | Validé |
| Vocabulary/tags/routing hints skippable | Validé |
| Modules/domains required | Validé |
| Activation minimum backend validé | Validé |
| AI does not produce roles/permissions/assignments | Validé |
| AI does not produce billing/subscription/pricing | Validé |
| Metrics MVP validées | Validé |
| Track post-activation corrections | Validé |
| Golden rule validée | Validé |

---

# 34. Points à traiter ailleurs

## 34.1 Event Catalog

À cadrer :
- payloads définitifs ;
- event persistence ;
- idempotence ;
- causation_id ;
- correlation_id ;
- consumers.

## 34.2 Notification Matrix

À cadrer :
- onboarding failed ;
- initial user invited ;
- establishment activated ;
- post-activation suggestions.

## 34.3 Admin / Support tooling

À cadrer :
- voir AIUsageLog ;
- voir failed onboarding interpretation ;
- relancer ;
- appliquer fallback templates.

## 34.4 Security / RGPD

À cadrer :
- retention outputs ;
- prompt logging ;
- DPA provider ;
- access admin/support.

---

# 35. Recommandation finale

Le contrat AI Onboarding est suffisamment cadré pour le MVP.

Décision centrale :

```txt
AI bootstraps.
Human validates.
Backend activates.
```

Le build doit maintenant s’appuyer sur :
- input minimal ;
- no user nominative data ;
- allowed catalogs stricts ;
- JSON schema par section ;
- caps par section ;
- validation backend ;
- validation humaine ;
- activation minimum ;
- fallback manuel/templates ;
- rerun post-activation sans mutation directe ;
- AIUsageLog systématique ;
- events corrélés.
