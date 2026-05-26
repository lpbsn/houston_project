# Houston — AI Observation Pipeline Contract

**Version:** v0.2  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Observation → AI Pipeline → Signal candidates  
**Documents liés:**  
- `Houston_ai_overview.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`
- `Houston_onboarding_domain.md`
- `Houston_rbac_permissions_domain.md`

---

# 1. Objectif du document

Ce document formalise le contrat du **AI Observation Pipeline** de Houston.

Il définit :
- le rôle du pipeline IA Observation ;
- les inputs envoyés à l’IA ;
- les données explicitement exclues ;
- le JSON schema attendu ;
- les outcomes possibles ;
- la structure des Signal candidates ;
- les règles de split ;
- les règles de domains ;
- les règles de tags / units / location ;
- les règles d’aggregation hints ;
- les validations backend obligatoires ;
- les retries / timeouts / failures ;
- les events liés ;
- les services backend recommandés ;
- les tests fonctionnels attendus.

Ce document est un contrat produit/tech.  
Il doit permettre d’implémenter le pipeline sans ambiguïté.

---

# 2. Principe central

```txt
AI produces Signal candidates.
Backend decides create / aggregate / no_signal_created.
```

En français :

```txt
L’IA produit des Signal candidates.
Le backend décide de créer, agréger ou ne créer aucun Signal.
```

---

# 3. Rappel des décisions AI Overview

## 3.1 Autorité

```txt
IA = moteur de structuration / suggestion / routing
Backend = autorité métier finale
```

## 3.2 Interdictions

L’IA ne peut pas :
- modifier directement la base ;
- créer directement un Signal ;
- créer une Action ;
- décider des permissions ;
- décider ou suggérer l’urgence au MVP ;
- résoudre ou annuler un Signal ;
- valider une Action ;
- assigner une Action ;
- envoyer des notifications.

## 3.3 Contrat JSON

Tous les outputs structurants doivent respecter un JSON schema strict.

## 3.4 Données IA

Le pipeline Observation reçoit uniquement du texte validé.

```txt
No audio
No image
Validated text only
```

---

# 4. Rôle du AI Observation Pipeline

## 4.1 Définition

Le AI Observation Pipeline analyse une Observation textuelle validée et propose un résultat structuré exploitable par le backend.

```txt
Observation.raw_text
        ↓
AI Observation Pipeline
        ↓
Structured proposal
        ↓
Backend validation
        ↓
Signal creation / aggregation / no_signal_created
```

## 4.2 Ce que le pipeline peut proposer

Le pipeline peut proposer :
- 0 à 5 Signal candidates ;
- un outcome `no_signal_created` ;
- des `detected_domains[]` avec confidence ;
- des runtime tags ;
- une operational unit ;
- un location text ;
- une synthèse structurée ;
- des aggregation hints ;
- des metadata de confiance.

## 4.3 Ce que le pipeline ne fait pas

Le pipeline ne :
- persiste rien ;
- ne crée pas de Signal en base ;
- ne choisit pas les permissions ;
- ne modifie pas les domains existants ;
- ne décide pas ou ne suggère pas l’urgence ;
- ne crée pas ou ne suggère pas d’Action ;
- ne lit pas les photos ;
- ne traite pas l’audio ;
- ne notifie pas directement les utilisateurs.

---

# 5. Workflow global

## 5.1 Flow standard

```txt
Observation submitted
        ↓
Observation persisted
        ↓
ObservationProcessing queued
        ↓
AIRequestStarted
        ↓
AI Observation Pipeline call
        ↓
AI structured output
        ↓
Backend schema validation
        ↓
Backend domain validation
        ↓
Backend create / aggregate / no_signal_created
        ↓
Events emitted
        ↓
Feeds updated
```

## 5.2 Flow depuis checklist

```txt
ChecklistTaskExecution
        ↓
+Signaler
        ↓
Observation source=checklist
        ↓
AI Observation Pipeline with checklist context
        ↓
Signal candidates
```

## 5.3 Flow audio

```txt
Audio
        ↓
AI Transcription
        ↓
User validates text
        ↓
Observation.raw_text
        ↓
AI Observation Pipeline
```

Le pipeline Observation ne reçoit jamais l’audio.

---

# 6. Input contract

## 6.1 Input général

Le backend envoie à l’IA un payload contrôlé.

```json
{
  "observation": {},
  "establishment_context": {},
  "checklist_context": null,
  "active_signals_context": [],
  "constraints": {},
  "metadata": {}
}
```

## 6.2 Observation input

```json
{
  "observation": {
    "id": "uuid",
    "raw_text": "Fuite d'eau devant la chambre 312",
    "source": "direct",
    "submitted_at": "2026-05-22T10:30:00Z"
  }
}
```

## 6.3 Observation source

Valeurs possibles :

```txt
direct
checklist
```

## 6.4 Establishment context

Le contexte établissement inclut :

```txt
establishment context
operational modules
operational domains
operational units
runtime vocabulary
routing hints
```

Exemple :

```json
{
  "establishment_context": {
    "establishment_id": "uuid",
    "establishment_name": "Mama Shelter Nice",
    "activity_description": "Hôtel avec restaurants, bar, rooftop, salles de séminaire et coworking.",
    "operational_modules": [
      "hotel",
      "restaurant",
      "bar",
      "rooftop",
      "seminar_rooms",
      "coworking"
    ],
    "operational_domains": [
      "maintenance",
      "housekeeping",
      "cleaning",
      "security",
      "guest_experience",
      "kitchen",
      "dining_room",
      "pricing",
      "event_management",
      "management"
    ],
    "operational_units": [
      "lobby",
      "rooms",
      "corridors",
      "restaurant",
      "kitchen",
      "bar",
      "rooftop",
      "seminar_rooms",
      "storage",
      "technical_rooms",
      "outdoor_areas"
    ],
    "runtime_vocabulary": [
      {
        "term": "roof",
        "meaning": "rooftop"
      },
      {
        "term": "la plonge",
        "meaning": "kitchen / washing area"
      },
      {
        "term": "chambre 312",
        "meaning": "rooms"
      },
      {
        "term": "coup de feu",
        "meaning": "restaurant rush"
      },
      {
        "term": "dans le jus",
        "meaning": "restaurant rush"
      },
      {
        "term": "la carte",
        "meaning": "restaurant menu"
      },
      {
        "term": "caisse",
        "meaning": "payment terminal / pricing / food_service depending context"
      },
      {
        "term": "PMS",
        "meaning": "hotel system"
      },
      {
        "term": "TPE",
        "meaning": "payment terminal"
      },
      {
        "term": "VRV",
        "meaning": "HVAC / maintenance"
      }
    ],
    "routing_hints": []
  }
}
```

## 6.5 Checklist context

Si l’Observation vient d’une checklist :

```json
{
  "checklist_context": {
    "checklist_execution_id": "uuid",
    "checklist_task_execution_id": "uuid",
    "template_title": "Ouverture restaurant",
    "task_title": "Vérifier chambre froide",
    "task_instructions": "Contrôler température et état général",
    "operational_unit": "kitchen"
  }
}
```

Si l’Observation ne vient pas d’une checklist :

```json
{
  "checklist_context": null
}
```

## 6.6 Active signals context

Le backend peut fournir un contexte limité des Signals actifs pertinents pour aider l’agrégation.

Uniquement Signals :

```txt
open
in_progress
```

Jamais :

```txt
resolved
canceled
archived
```

Limite :

```txt
max_active_signals_context = 20
```

Sélection recommandée :
- domains compatibles ;
- operational unit compatible ;
- mots-clés proches ;
- récence ;
- Signals les plus actifs.

Payload recommandé :

```json
{
  "active_signals_context": [
    {
      "signal_id": "uuid",
      "title": "Fuite d'eau devant la chambre 312",
      "structured_summary": "Fuite signalée dans la zone chambres, devant la chambre 312.",
      "detected_domains": ["maintenance", "housekeeping"],
      "operational_unit": "rooms",
      "location_text": "chambre 312",
      "status": "open",
      "candidate_signal_count": 2,
      "created_at": "2026-05-22T09:45:00Z"
    }
  ]
}
```

## 6.7 Constraints

Le backend envoie les contraintes métier.

```json
{
  "constraints": {
    "max_signal_candidates": 5,
    "max_detected_domains_per_signal": 4,
    "max_active_signals_context": 20,
    "allowed_domains": [
      "maintenance",
      "housekeeping",
      "cleaning",
      "security",
      "guest_experience",
      "kitchen",
      "dining_room",
      "pricing",
      "event_management",
      "management"
    ],
    "allowed_units": [
      "lobby",
      "rooms",
      "corridors",
      "restaurant",
      "kitchen",
      "bar",
      "rooftop",
      "seminar_rooms",
      "storage",
      "technical_rooms",
      "outdoor_areas"
    ],
    "urgency_output_allowed": false,
    "action_suggestion_allowed": false,
    "image_analysis_allowed": false
  }
}
```

## 6.8 Metadata

```json
{
  "metadata": {
    "correlation_id": "uuid",
    "ai_domain": "observation_pipeline",
    "prompt_version": "observation_pipeline_v1",
    "locale": "fr-FR"
  }
}
```

---

# 7. Données exclues du pipeline

## 7.1 Audio

L’audio n’est jamais envoyé au pipeline Observation.

```txt
Audio → transcription → validated text → Observation Pipeline
```

## 7.2 Images

Les photos ne sont jamais envoyées à l’IA au MVP.

```txt
Photos = contexte humain uniquement
```

## 7.3 Prompts complets en logs

Les prompts complets ne doivent pas être stockés dans les logs standards.

## 7.4 Données non nécessaires

Ne pas envoyer :
- données utilisateurs non nécessaires ;
- emails ;
- numéros de téléphone ;
- historique complet de l’établissement ;
- Actions non pertinentes ;
- Signals resolved/canceled/archived ;
- photos ;
- audio.

---

# 8. Output contract

## 8.1 Structure globale

Le pipeline doit retourner un JSON strict.

```json
{
  "schema_version": "observation_pipeline_output_v1",
  "outcome": "signals_proposed",
  "signal_candidates": [],
  "no_signal_reason": null,
  "processing_notes": []
}
```

## 8.2 Outcomes possibles

```txt
signals_proposed
no_signal_created
invalid_input
```

## 8.3 signals_proposed

Utilisé quand l’IA propose 1 à 5 Signal candidates.

## 8.4 no_signal_created

Utilisé quand l’Observation ne nécessite pas de Signal opérationnel.

Backend :

```txt
ObservationProcessing.status = processed
ObservationProcessing.outcome = no_signal_created
```

## 8.5 invalid_input

Utilisé si l’IA estime que l’input ne peut pas être traité.

Important :

```txt
invalid_input is not exposed directly to user.
Backend decides retry, failed, or no_signal_created.
```

---

# 9. Signal candidate schema

## 9.1 Structure d’un Signal candidate

```json
{
  "signal_candidate_id": "candidate_1",
  "title": "Fuite d'eau devant la chambre 312",
  "structured_summary": "Une fuite d'eau est signalée devant la chambre 312. La zone doit être contrôlée et sécurisée.",
  "detected_domains": [
    {
      "domain": "maintenance",
      "confidence": 0.94
    },
    {
      "domain": "housekeeping",
      "confidence": 0.71
    }
  ],
  "runtime_tags": [
    "water_leak",
    "room_area"
  ],
  "operational_unit": "rooms",
  "location_text": "chambre 312",
  "aggregation_hint": {
    "should_aggregate": true,
    "target_signal_id": "uuid",
    "confidence": 0.86,
    "reason": "Same location and same water leak problem as existing open Signal."
  },
  "confidence_score": 0.91
}
```

## 9.2 Champs obligatoires

```txt
signal_candidate_id
title
structured_summary
detected_domains[]
confidence_score
```

## 9.3 Champs optionnels

```txt
runtime_tags[]
operational_unit
location_text
aggregation_hint
```

## 9.4 Interdiction urgency

Le pipeline ne doit pas retourner d’urgence au MVP.

```txt
urgency_suggestion = forbidden MVP
```

## 9.5 Interdiction action suggestion

Le pipeline ne doit pas retourner d’Actions suggérées au MVP.

```txt
suggested_actions = forbidden MVP
```

---

# 10. JSON schema conceptuel

```json
{
  "type": "object",
  "required": ["schema_version", "outcome", "signal_candidates"],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "observation_pipeline_output_v1"
    },
    "outcome": {
      "type": "string",
      "enum": ["signals_proposed", "no_signal_created", "invalid_input"]
    },
    "signal_candidates": {
      "type": "array",
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": [
          "signal_candidate_id",
          "title",
          "structured_summary",
          "detected_domains",
          "confidence_score"
        ],
        "properties": {
          "signal_candidate_id": {
            "type": "string"
          },
          "title": {
            "type": "string",
            "minLength": 5,
            "maxLength": 120
          },
          "structured_summary": {
            "type": "string",
            "minLength": 10,
            "maxLength": 1000
          },
          "detected_domains": {
            "type": "array",
            "minItems": 1,
            "maxItems": 4,
            "items": {
              "type": "object",
              "required": ["domain", "confidence"],
              "properties": {
                "domain": {
                  "type": "string"
                },
                "confidence": {
                  "type": "number",
                  "minimum": 0,
                  "maximum": 1
                }
              }
            }
          },
          "runtime_tags": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "operational_unit": {
            "type": ["string", "null"]
          },
          "location_text": {
            "type": ["string", "null"]
          },
          "aggregation_hint": {
            "type": ["object", "null"],
            "properties": {
              "should_aggregate": {
                "type": "boolean"
              },
              "target_signal_id": {
                "type": ["string", "null"]
              },
              "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
              },
              "reason": {
                "type": ["string", "null"]
              }
            }
          },
          "confidence_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        }
      }
    },
    "no_signal_reason": {
      "type": ["string", "null"]
    },
    "processing_notes": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
```

---

# 11. Outcome rules

## 11.1 signals_proposed

```txt
outcome = signals_proposed
requires signal_candidates.size between 1 and 5
```

## 11.2 no_signal_created

```txt
outcome = no_signal_created
requires signal_candidates.size = 0
requires no_signal_reason present
```

Backend :

```txt
ObservationProcessing.status = processed
ObservationProcessing.outcome = no_signal_created
```

UX :

```txt
Observation non exploitable
```

ou :

```txt
Aucun Signal nécessaire
```

## 11.3 invalid_input

```txt
outcome = invalid_input
signal_candidates.size = 0
```

Backend décide :
- retry ;
- failed ;
- no_signal_created.

Ne jamais exposer `invalid_input` tel quel à l’utilisateur.

---

# 12. Split logic

## 12.1 Principe

Une Observation peut contenir plusieurs situations opérationnelles.

```txt
1 Observation
→ 0 to 5 Signal candidates
```

## 12.2 Quand splitter

Splitter uniquement si plusieurs situations opérationnelles distinctes sont présentes.

Exemple :

```txt
"Fuite chambre 312 et TPE rooftop HS"
→ 2 Signal candidates
```

## 12.3 Quand ne pas splitter

Ne pas splitter si les détails décrivent le même problème opérationnel.

Exemple :

```txt
"Fuite chambre 312, sol mouillé, serviettes au sol"
→ 1 Signal candidate
```

## 12.4 Max candidates

```txt
max_signal_candidates = 5
```

## 12.5 Si l’IA retourne plus de 5 candidates

Backend garde les 5 candidates les plus pertinentes selon `confidence_score`.

```txt
Keep top 5 by confidence_score.
Log technical warning.
```

---

# 13. Domain detection

## 13.1 detected_domains requis

Chaque Signal candidate doit avoir au moins un detected_domain valide.

```txt
detected_domains.size >= 1
```

## 13.2 Max domains

```txt
max_detected_domains_per_signal = 4
```

## 13.3 Domain inconnu

Si l’IA retourne un domain non présent dans l’établissement :

```txt
Backend removes unknown domain.
```

Si plus aucun domain valide ne reste :

```txt
Signal candidate invalid.
```

## 13.4 Plus de 4 domains

Backend garde les 4 domains valides les plus confiants.

```txt
Keep top 4 valid domains by confidence.
```

## 13.5 Confidence score domain

Chaque domain doit avoir :

```txt
confidence between 0 and 1
```

## 13.6 Seuil confidence

Décision MVP :

```txt
No blocking confidence threshold MVP.
```

Confidence est utilisée pour :
- tri ;
- notification level ;
- analytics ;
- debug ;
- mesure qualité IA.

## 13.7 Permissions

Confidence ne crée pas de permission séparée.

---

# 14. Operational units and location

## 14.1 operational_unit

L’IA peut proposer une operational_unit.

```txt
operational_unit optional
```

Le backend accepte seulement les units validées.

## 14.2 Unit inconnue

Si unit inconnue :

```txt
operational_unit = null
location_text preserved
```

Ne pas créer automatiquement une nouvelle unit au MVP.

## 14.3 location_text

`location_text` est optionnel, mais fortement recommandé si une localisation est détectée.

Exemples :
- chambre 312 ;
- devant l’ascenseur ;
- rooftop ;
- caisse bar ;
- salle séminaire 2.

## 14.4 Rooms

Pas de création exhaustive des chambres.

```txt
"chambre 312"
→ operational_unit = rooms
→ location_text = chambre 312
```

---

# 15. Runtime tags

## 15.1 Rôle

Les runtime_tags enrichissent la situation.

Exemples :
- water_leak ;
- payment_terminal ;
- restaurant_rush ;
- hvac ;
- guest_complaint ;
- safety_risk.

## 15.2 Validation

Runtime tags proposés librement.

Le backend peut :
- normaliser ;
- filtrer ;
- ignorer.

## 15.3 Permissions

Les tags ne pilotent pas les permissions.

```txt
Runtime tags ≠ RBAC
```

---

# 16. Aggregation hints

## 16.1 Rôle

L’IA peut proposer un aggregation_hint.

Mais le backend décide.

```txt
AI suggests aggregation.
Backend validates or ignores.
```

## 16.2 Structure

```json
{
  "aggregation_hint": {
    "should_aggregate": true,
    "target_signal_id": "uuid",
    "confidence": 0.86,
    "reason": "Same problem and location as existing open Signal."
  }
}
```

## 16.3 Backend validation aggregation

Le backend doit vérifier :
- target_signal_id existe ;
- même establishment ;
- target status open/in_progress ;
- target non archived/canceled/resolved ;
- domains compatibles ;
- contexte compatible ;
- observation/candidate pas déjà linked ;
- pas de duplicate processing.

## 16.4 Aggregation allowed statuses

```txt
open
in_progress
```

## 16.5 Aggregation forbidden statuses

```txt
resolved
canceled
archived
```

## 16.6 Hint vers Signal resolved/canceled/archived

Backend ignore l’hint.

Si la candidate est valide :

```txt
Create new Signal.
```

## 16.7 Aggregation hint invalide

Si aggregation_hint invalide mais candidate valide :

```txt
Ignore aggregation_hint.
Process candidate normally.
```

## 16.8 Backend matching complémentaire

Le backend fait son propre matching / validation d’aggregation avant create/aggregate.

```txt
AI hint is not authoritative.
```

---

# 17. Backend validation pipeline

## 17.1 Validation stages

```txt
AI output
        ↓
JSON parse validation
        ↓
JSON schema validation
        ↓
Domain validation
        ↓
Unit validation
        ↓
Candidate validation
        ↓
Aggregation validation
        ↓
Persistence decision
```

## 17.2 JSON parse validation

Si JSON non parseable :

```txt
Retry if attempts remain.
Failed if max attempts reached.
```

## 17.3 Schema validation

Si schema invalide :
- retry selon policy ;
- failed si max attempts ;
- admin/support visible ;
- UX simplifiée.

## 17.4 Domain validation

Vérifier :
- domains existants ;
- max 4 ;
- confidence valid ;
- minimum 1 valid domain.

## 17.5 Unit validation

Vérifier :
- unit présente dans les units établissement ;
- sinon unit ignorée ;
- location_text conservé.

## 17.6 Candidate validation

Vérifier :
- signal_candidate_id présent ;
- title présent ;
- summary présent ;
- confidence_score entre 0 et 1 ;
- not duplicate within same output ;
- candidate count <= 5 ;
- domain valid.

## 17.7 Aggregation validation

Vérifier :
- target active ;
- target same establishment ;
- target status open/in_progress ;
- compatible domains/context.

## 17.8 Persistence decision

Pour chaque valid candidate :
- create new Signal ;
- or aggregate into existing Signal.

---

# 18. Persistence rules

## 18.1 AI does not persist

L’IA ne persiste rien.

## 18.2 Backend creates Signal

Si candidate valide distincte :

```txt
SignalCreated
ObservationLinkedToSignal
```

## 18.3 Backend aggregates Signal candidate

Si candidate valide agrégée :

```txt
SignalAggregated
ObservationLinkedToSignal
candidate_signal_count += 1
```

## 18.4 Backend no signal

Si outcome no_signal_created :

```txt
ObservationProcessing.status = processed
ObservationProcessing.outcome = no_signal_created
ObservationMarkedNotActionable
```

## 18.5 ObservationSignalLink

Créer un lien pour chaque candidate persistée/agrégée.

```txt
ObservationSignalLink
├── observation_id
├── signal_id
├── relation_type
│   ├── created
│   ├── aggregated
│   └── split_created
├── signal_candidate_id
├── candidate_signal_index
└── timestamps
```

---

# 19. Status updates

## 19.1 ObservationProcessing statuses

```txt
queued
processing
processed
retrying
failed
```

## 19.2 Start processing

```txt
queued → processing
```

Events :
- AIRequestStarted
- ObservationProcessingStarted

## 19.3 Success

```txt
processing → processed
```

Events :
- AIRequestSucceeded
- ObservationProcessingSucceeded

## 19.4 Retry

```txt
processing → retrying → queued/processing
```

Events :
- AIRequestRetried

## 19.5 Failed

```txt
processing/retrying → failed
```

Events :
- AIRequestFailed
- ObservationProcessingFailed

---

# 20. Timeouts and retries

## 20.1 Timeout

```txt
Observation Pipeline timeout = 20s
```

## 20.2 Retry

```txt
max_attempts = 3
```

## 20.3 Retryable errors

Retry if:
- provider timeout ;
- temporary provider error ;
- rate limit temporary ;
- invalid JSON ;
- network issue.

## 20.4 Non-retryable errors

Do not retry if:
- Observation deleted / unavailable ;
- establishment context missing ;
- schema version unsupported by backend ;
- invalid internal configuration ;
- no valid domains in establishment.

## 20.5 Failed UX

Auteur voit message simplifié :

```txt
Analyse temporairement impossible. Réessai en cours.
```

ou si final failed :

```txt
Analyse impossible pour le moment.
```

Admin/support voit le détail technique.

---

# 21. Error codes

## 21.1 Error codes recommandés

```txt
provider_timeout
provider_unavailable
rate_limited
invalid_json
schema_validation_failed
invalid_domain
invalid_unit
too_many_candidates
no_valid_candidate
aggregation_target_invalid
establishment_context_missing
checklist_context_invalid
max_attempts_reached
unknown_error
```

## 21.2 Storage

Stocker dans :

```txt
ObservationProcessing.last_error_code
AIUsageLog.error_code
```

## 21.3 User-facing message

Ne jamais afficher error_code brut à l’utilisateur terrain.

---

# 22. AIUsageLog

## 22.1 Log obligatoire

Chaque call Observation Pipeline crée un AIUsageLog.

## 22.2 Champs

```txt
AIUsageLog
├── establishment_id
├── ai_domain = observation_pipeline
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

## 22.3 Prompt version

```txt
prompt_version = observation_pipeline_v1
```

---

# 23. Stockage technique outputs IA

## 23.1 Décision

Stockage temporaire des outputs structurés.

```txt
retention = 14 jours
```

## 23.2 Objectif

Permettre :
- debug ;
- audit technique ;
- analyse qualité IA ;
- comparaison provider/model/prompt_version.

## 23.3 Pas de stockage long

Ne pas stocker durablement :
- prompts complets ;
- audio ;
- images ;
- contenus non nécessaires.

---

# 24. Events

## 24.1 Events minimum validés

```txt
AIRequestStarted
AIRequestSucceeded
AIRequestFailed
AIRequestRetried
ObservationProcessingStarted
ObservationProcessingSucceeded
ObservationProcessingFailed
ObservationLinkedToSignal
ObservationMarkedNotActionable
SignalCreated
SignalAggregated
```

## 24.2 Le pipeline ne notifie jamais directement

Le pipeline émet des events.

```txt
Notification Matrix decides notifications.
```

## 24.3 Event correlation

All events should carry:

```txt
correlation_id
establishment_id
observation_id when relevant
```

---

# 25. Prompt contract

## 25.1 Prompt objective

The prompt must instruct the model to:
- analyze only validated text ;
- use only allowed domains ;
- use only allowed units ;
- return strict JSON ;
- propose 0 to 5 Signal candidates ;
- never suggest urgency ;
- never suggest actions ;
- prefer aggregation if active similar signal exists ;
- avoid over-splitting ;
- preserve operational clarity ;
- output no_signal_created if no operational situation.

## 25.2 Prompt guardrails

Prompt must state:

```txt
You do not persist data.
You do not decide permissions.
You do not create Actions.
You do not decide or suggest urgency.
You must only use allowed domains.
You must only use allowed units.
You must output JSON matching schema.
```

## 25.3 Language

For MVP France :

```txt
Input likely French.
Output fields should be stable keys in English.
Text values can be French for title and summary.
```

---

# 26. Backend services recommandés

## 26.1 Observations::QueueForAI

Responsabilités :
- create ObservationProcessing ;
- enqueue job ;
- emit ObservationQueuedForAI.

## 26.2 Observations::ProcessWithAIJob

Responsabilités :
- lock processing ;
- load Observation ;
- load context ;
- call AI service ;
- update processing status.

## 26.3 Ai::ObservationPipeline::BuildInput

Responsabilités :
- build input payload ;
- minimize context ;
- include checklist context if present ;
- include active signals context ;
- include constraints.

## 26.4 Ai::ObservationPipeline::AnalyzeObservation

Responsabilités :
- call provider ;
- enforce timeout ;
- log AIUsageLog ;
- return raw structured output.

## 26.5 Ai::ObservationPipeline::ValidateOutput

Responsabilités :
- JSON schema validation ;
- domain validation ;
- unit validation ;
- candidate validation ;
- aggregation_hint validation.

## 26.6 Signals::CreateFromCandidate

Responsabilités :
- persist Signal ;
- create ObservationSignalLink ;
- emit SignalCreated.

## 26.7 Signals::AggregateCandidate

Responsabilités :
- validate target ;
- increment candidate_signal_count ;
- create ObservationSignalLink ;
- emit SignalAggregated.

## 26.8 Observations::MarkNotActionable

Responsabilités :
- set outcome no_signal_created ;
- emit ObservationMarkedNotActionable.

---

# 27. Model/data implications

## 27.1 observation_processings

```txt
observation_processings
├── id
├── observation_id
├── status
├── outcome
├── attempts
├── last_error_code
├── last_error_message
├── queued_at
├── processing_started_at
├── processed_at
├── failed_at
├── correlation_id
├── created_at
└── updated_at
```

## 27.2 observation_signal_links

```txt
observation_signal_links
├── id
├── observation_id
├── signal_id
├── relation_type
├── signal_candidate_id
├── candidate_signal_index
├── created_at
└── updated_at
```

## 27.3 ai_structured_outputs

Optional technical table with 14-day retention:

```txt
ai_structured_outputs
├── id
├── ai_usage_log_id
├── establishment_id
├── observation_id
├── output_json
├── expires_at
├── created_at
└── updated_at
```

---

# 28. Edge cases

## 28.1 AI returns 0 candidates with signals_proposed

Invalid.

Backend should:
- retry if attempts remain ;
- else failed with `schema_validation_failed`.

## 28.2 AI returns candidates with no domain

Invalid candidate.

If no valid candidates remain:
- retry or failed ;
- do not create Signal without domain.

## 28.3 AI returns unknown domain

Backend removes unknown domain.

If candidate has no valid domain left:
- candidate invalid.

## 28.4 AI returns more than 4 domains

Backend keeps top 4 valid domains by confidence.

## 28.5 AI returns more than 5 candidates

Backend keeps top 5 by confidence_score.

## 28.6 AI suggests urgency

Ignore.

Also log schema warning if urgency field appears.

## 28.7 AI suggests actions

Ignore.

Also log schema warning if suggested_actions appears.

## 28.8 Aggregation target resolved

Reject aggregation hint.

Create new Signal if candidate valid.

## 28.9 Aggregation target canceled/archived

Reject aggregation hint.

Create new Signal if candidate valid.

## 28.10 Observation from checklist with short text

Allowed if checklist context is present and sufficient.

## 28.11 Photos attached

Do not send photos to AI.

Signal may later display media from ObservationMedia through product UI rules.

## 28.12 Audio source

Pipeline sees only validated transcription.

## 28.13 Duplicate candidate within same output

Backend should deduplicate by title/context/domain similarity before persistence.

---

# 29. Metrics MVP

## 29.1 Metrics validées

```txt
candidates per Observation
no_signal_created rate
SignalCreated vs SignalAggregated
aggregation_hint accepted/rejected
invalid_json rate
invalid_domain rate
manager domain correction rate
average detected_domains count
latency
cost per Observation
```

## 29.2 Pourquoi

Ces metrics servent à :
- mesurer la qualité du pipeline ;
- mesurer le coût ;
- détecter sur-split / sous-split ;
- détecter mauvaise détection de domains ;
- détecter mauvaise aggregation ;
- préparer l'amélioration post-pilote.

---

# 30. Tests fonctionnels MVP

## 30.1 Valid Observation creates Signal

```txt
Given valid Observation raw_text
And AI returns one valid Signal candidate
When backend processes output
Then Signal is created
And ObservationSignalLink is created
And SignalCreated is emitted
```

## 30.2 Multiple candidates create multiple Signals

```txt
Given AI returns 3 valid Signal candidates
When processing completes
Then up to 3 Signals are created/aggregated
And outcome = multiple_signals_created
```

## 30.3 No signal created

```txt
Given AI returns outcome no_signal_created
When backend validates output
Then no Signal is created
And ObservationProcessing outcome = no_signal_created
And ObservationMarkedNotActionable is emitted
```

## 30.4 Unknown domain rejected

```txt
Given AI returns domain not in establishment domains
When backend validates output
Then domain is removed or candidate invalidated
```

## 30.5 Max 4 domains

```txt
Given AI returns 6 valid domains
When backend validates candidate
Then only top 4 domains are kept
```

## 30.6 Max 5 candidates

```txt
Given AI returns 8 candidates
When backend validates output
Then only top 5 are processed
```

## 30.7 Aggregation to open Signal

```txt
Given existing open Signal
And AI returns aggregation_hint targeting it
When backend validates hint
Then candidate is aggregated
And SignalAggregated is emitted
```

## 30.8 Aggregation to resolved rejected

```txt
Given existing resolved Signal
And AI returns aggregation_hint targeting it
When backend validates hint
Then aggregation is rejected
And new Signal is created if candidate valid
```

## 30.9 Invalid JSON retry

```txt
Given provider returns invalid JSON
When processing occurs
Then retry is attempted if attempts remain
And AIRequestRetried is emitted
```

## 30.10 Timeout failure

```txt
Given provider timeout > 20s
When call times out
Then ObservationProcessing enters retrying or failed
And AIUsageLog error_code = provider_timeout
```

## 30.11 No image sent

```txt
Given Observation has photos
When AI input is built
Then payload contains no image data
```

## 30.12 Checklist context included

```txt
Given Observation source checklist
When AI input is built
Then checklist_execution_id and task context are included
```

---

# 31. Décisions validées — index

| Décision | Statut |
|---|---:|
| Pipeline propose 0 à 5 Signal candidates | Validé |
| Backend décide create / aggregate / no_signal_created | Validé |
| Input = raw_text + source + establishment context + checklist context optionnel + active Signals pertinents | Validé |
| Audio jamais envoyé | Validé |
| Images jamais envoyées | Validé |
| Outcomes = signals_proposed / no_signal_created / invalid_input | Validé |
| no_signal_created outcome normal | Validé |
| invalid_input non exposé utilisateur | Validé |
| Max 5 Signal candidates | Validé |
| Si >5, backend garde top 5 par confidence_score | Validé |
| Split seulement situations distinctes | Validé |
| Ne pas splitter détails d’une même situation | Validé |
| Required candidate fields validés | Validé |
| Optional candidate fields validés | Validé |
| Pas d’urgence IA MVP | Validé |
| Pas d’Actions suggérées MVP | Validé |
| detected_domains min 1 valide | Validé |
| Max 4 domains | Validé |
| Domain inconnu supprimé | Validé |
| Candidate invalide si aucun domain valide | Validé |
| Si >4 domains, backend garde top 4 par confidence | Validé |
| Pas de seuil confidence bloquant | Validé |
| operational_unit optionnelle, validée backend | Validé |
| Unit inconnue ignorée, location_text conservé | Validé |
| location_text optionnel recommandé | Validé |
| runtime_tags libres, normalisables/filtrables | Validé |
| aggregation_hint non autoritaire | Validé |
| Active Signals envoyés = open/in_progress uniquement | Validé |
| Max 20 active Signals | Validé |
| Pas d’aggregation resolved/canceled/archived | Validé |
| Hint vers resolved ignoré | Validé |
| Hint invalide ignoré si candidate valide | Validé |
| Backend matching aggregation complémentaire | Validé |
| Outputs IA structurés stockés 14 jours | Validé |
| JSON invalide = retry puis failed | Validé |
| Max attempts = 3 | Validé |
| Timeout = 20s | Validé |
| Erreurs techniques invisibles utilisateur | Validé |
| Events minimum validés | Validé |
| Pipeline ne notifie jamais directement | Validé |
| Metrics MVP validées | Validé |

---

# 32. Points à traiter dans d'autres documents

## 32.1 AI Onboarding Contract

À traiter :
- onboarding input schema ;
- proposals schema ;
- modules/domains/units/vocabulary/routing hints ;
- validation human workflow.

## 32.2 AI Transcription Contract

À traiter :
- audio lifecycle ;
- provider call ;
- transcription output ;
- confidence ;
- user validation ;
- deletion.

## 32.3 Event Catalog

À traiter :
- event persistence ;
- correlation_id ;
- causation_id ;
- payloads définitifs ;
- consumers.

## 32.4 Notification Matrix

À traiter :
- notifications triggered by SignalCreated ;
- SignalAggregated ;
- Observation processing failed ;
- domain routing.

---

# 33. Recommandation finale

Le AI Observation Pipeline Contract est maintenant cadré explicitement et validé.

Décision centrale :

```txt
AI produces Signal candidates.
Backend decides create / aggregate / no_signal_created.
```

Le build doit maintenant s’appuyer sur :
- input minimal et contextualisé ;
- no audio/images sent ;
- JSON schema strict ;
- backend validation ;
- max 5 candidates ;
- max 4 domains ;
- no urgency/action suggestions ;
- aggregation hints non autoritaires ;
- max 20 active Signals context ;
- retries/timeouts contrôlés ;
- AIUsageLog systématique ;
- events corrélés.

La prochaine étape logique est :

```txt
Houston_ai_onboarding_contract.md
```

ou, si priorité terrain audio :

```txt
Houston_ai_transcription_contract.md
```
