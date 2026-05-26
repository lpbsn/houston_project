# Houston — AI Overview

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — AI principles and shared governance  
**Documents liés:**  
- `Houston_mvp_cadrage_p0.md`
- `Houston_onboarding_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`

---

# 1. Objectif du document

Ce document formalise la vision transversale de l'IA dans Houston.

Il définit :
- le rôle général de l'IA ;
- ses limites ;
- les responsabilités backend / humain / IA ;
- les sous-domaines IA ;
- les principes de validation ;
- les règles de provider ;
- les logs ;
- le tracking coût / usage ;
- les règles de privacy / RGPD ;
- les timeouts ;
- les retries ;
- les fallbacks ;
- les events IA transverses.

Ce document ne remplace pas les contrats IA détaillés.

Il sert de document chapeau pour :
- `Houston_ai_onboarding_contract.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_ai_transcription_contract.md`

---

# 2. Règle d'or

```txt
AI proposes.
Backend validates.
Humans control structural and operational authority.
```

En français :

```txt
L'IA propose.
Le backend valide.
L'humain contrôle les décisions structurantes et opérationnelles.
```

---

# 3. Rôle général de l'IA

## 3.1 Définition

Dans Houston, l'IA est :

```txt
moteur de transcription
+
moteur d'assistance
+
moteur de structuration
+
moteur de suggestion
+
moteur de routing
```

## 3.2 Autorité métier

Le backend reste l'autorité métier finale.

```txt
Backend = source of truth
AI = proposal engine
```

## 3.3 Ce que l'IA peut faire

L'IA peut :
- transcrire un audio ;
- structurer une Observation ;
- proposer des Signal candidates ;
- proposer des detected_domains ;
- proposer des runtime tags ;
- proposer des routing hints ;
- proposer des modules/domains/units/vocabulary pendant onboarding ;
- aider à l'agrégation ;
- produire des outputs JSON structurés.

## 3.4 Ce que l'IA ne peut pas faire

L'IA ne peut pas :
- modifier directement la base ;
- créer directement un Signal en base ;
- créer directement une Action ;
- décider des permissions ;
- modifier un lifecycle ;
- résoudre un Signal ;
- annuler un Signal ;
- valider une Action ;
- assigner une Action ;
- activer une configuration onboarding sans validation humaine ;
- envoyer des notifications directement.

---

# 4. Responsabilités

## 4.1 IA

L'IA produit des propositions structurées.

```txt
AI output = proposal
```

## 4.2 Backend

Le backend :
- valide les outputs IA ;
- rejette les outputs invalides ;
- transforme les propositions en objets métier ;
- applique les règles métier ;
- applique RBAC ;
- persiste les données ;
- émet les events ;
- gère retries/failures ;
- logge les métadonnées techniques.

## 4.3 Humain

L'humain contrôle :
- les décisions structurantes ;
- les validations onboarding ;
- la validation transcription au moment du submit ;
- l'urgence Signal ;
- les corrections de domains ;
- les décisions opérationnelles : actions, validation, cancel, resolve.

---

# 5. Sous-domaines IA

## 5.1 Découpage documentaire

```txt
AI Overview
├── AI Onboarding Contract
├── AI Observation Pipeline Contract
└── AI Transcription Contract
```

## 5.2 AI Onboarding

Rôle :
- analyser la description établissement ;
- proposer modules/domains/units/tags/vocabulary/routing hints ;
- fournir un bootstrap runtime initial.

Validation :
- validation humaine obligatoire avant activation.

## 5.3 AI Observation Pipeline

Rôle :
- analyser une Observation textuelle validée ;
- proposer 0 à 5 Signal candidates ;
- proposer detected_domains ;
- proposer tags/context ;
- proposer des hypothèses d'agrégation.

Validation :
- validation backend obligatoire ;
- pas de validation humaine systématique MVP.

## 5.4 AI Transcription

Rôle :
- transformer un audio temporaire en texte éditable.

Validation :
- validation utilisateur implicite quand il submit l'Observation.

---

# 6. Database mutation

## 6.1 Décision

L'IA ne modifie jamais directement la base de données.

```txt
AI never writes directly to DB.
```

## 6.2 Flow standard

```txt
AI returns structured proposal
        ↓
Backend validates
        ↓
Backend transforms
        ↓
Backend persists
        ↓
Backend emits events
```

## 6.3 Pourquoi

Cette règle garantit :
- sécurité ;
- auditabilité ;
- testabilité ;
- contrôle métier ;
- respect du RBAC ;
- réduction des effets non déterministes de l'IA.

---

# 7. JSON schemas

## 7.1 Décision

Tous les outputs IA structurants doivent respecter un JSON schema strict.

```txt
Strict JSON schema required for all structuring AI outputs.
```

## 7.2 Outputs concernés

Sont concernés :
- onboarding proposals ;
- observation pipeline outputs ;
- Signal candidates ;
- detected_domains ;
- routing hints ;
- structured summaries.

## 7.3 Transcription

La transcription retourne principalement du texte.

Même si elle n'est pas un output métier structurant complexe, elle doit être encapsulée dans une réponse technique contrôlée.

Exemple :

```json
{
  "transcription": "Il y a une fuite devant la chambre 312",
  "language": "fr",
  "confidence": 0.91
}
```

## 7.4 Invalid JSON

Si un output structurant ne respecte pas le schema :
- backend rejette ;
- retry selon politique du domaine IA ;
- log technique ;
- éventuel status failed ;
- UX simplifiée.

---

# 8. Validation des outputs IA

## 8.1 Backend validation

Le backend valide toujours les outputs IA.

```txt
Backend validation is mandatory.
```

## 8.2 Human validation by AI domain

| AI domain | Human validation |
|---|---|
| Onboarding | Oui, obligatoire |
| Observation Pipeline | Non systématique, backend validation suffit |
| Transcription | Oui, implicite par l'utilisateur au submit Observation |

## 8.3 Onboarding

L'IA propose, mais l'humain valide avant activation runtime.

## 8.4 Observation Pipeline

L'IA propose des structures.

Le backend valide :
- domains existants ;
- limits ;
- JSON ;
- statut des Signals ;
- règles d'agrégation ;
- establishment scope.

## 8.5 Transcription

L'utilisateur valide la transcription en soumettant l'Observation.

```txt
Submit Observation = user validates transcription.
```

---

# 9. Provider strategy

## 9.1 Décision

Créer une abstraction provider simple.

```txt
One active provider MVP.
Provider replaceable later.
```

## 9.2 Structure technique recommandée

```txt
Ai::Providers::Base
Ai::Providers::OpenAI
Ai::Providers::Ollama / Local optional dev
```

## 9.3 Production

Production utilise un provider stable.

```txt
Prod = stable provider
```

## 9.4 Local dev

LLM local possible en dev.

```txt
Local LLM = optional dev tool
Not guaranteed production provider
```

## 9.5 Pourquoi abstraction simple

L'abstraction évite :
- coupling fort à un provider ;
- dette technique ;
- difficulté de fallback ;
- migration coûteuse ;
- tests trop dépendants d'un SDK.

---

# 10. API keys / BYOK

## 10.1 Décision MVP

```txt
MVP = clé IA plateforme.
```

## 10.2 Tracking par établissement

Même avec clé plateforme, usage tracking obligatoire par établissement.

```txt
AI usage tracking by establishment required.
```

## 10.3 Post-MVP

Post-MVP :

```txt
BYOK
ou
clé IA par établissement
```

## 10.4 Pourquoi pas BYOK MVP

BYOK dès MVP ajoute :
- stockage sécurisé des secrets ;
- rotation de clés ;
- erreurs client ;
- support ;
- billing complexe ;
- onboarding plus lourd.

Pour le pilote, la valeur est faible.

---

# 11. AI usage tracking

## 11.1 Décision

AI usage tracking obligatoire dès le MVP.

Tracking par :
- établissement ;
- type d'IA ;
- provider ;
- model ;
- tokens ;
- durée ;
- coût estimé ;
- status ;
- erreurs.

## 11.2 Objectifs

Le tracking sert à :
- comprendre le coût réel ;
- préparer le pricing ;
- surveiller la marge ;
- identifier les erreurs ;
- comparer providers ;
- mesurer les performances ;
- détecter les abus.

---

# 12. AIUsageLog

## 12.1 Décision

Un `AIUsageLog` commun couvre tous les sous-domaines IA.

```txt
AIUsageLog common to all AI domains.
```

## 12.2 Champs recommandés

```txt
AIUsageLog
├── id UUID
├── establishment_id UUID nullable if global/onboarding pre-establishment
├── ai_domain enum
│   ├── onboarding
│   ├── observation_pipeline
│   └── transcription
├── provider string
├── model string
├── prompt_version string nullable for transcription if not applicable
├── status enum
│   ├── started
│   ├── succeeded
│   ├── failed
│   └── retried
├── latency_ms integer
├── input_tokens integer nullable
├── output_tokens integer nullable
├── cost_estimate decimal nullable
├── error_code string nullable
├── correlation_id string
├── created_at datetime
└── updated_at datetime
```

## 12.3 Chaque AI call log contient

```txt
provider
model
prompt_version
latency
token_count
status
cost_estimate
```

## 12.4 Correlation

`correlation_id` est obligatoire pour relier :
- ObservationProcessing ;
- OnboardingSession ;
- Transcription request ;
- events ;
- logs techniques ;
- AIUsageLog.

---

# 13. Prompt strategy

## 13.1 Prompts séparés par domaine

Décision :

```txt
Prompts séparés par domaine IA.
```

Prompts :
- onboarding ;
- observation pipeline ;
- transcription wrapper si nécessaire.

## 13.2 Principes communs

Les principes communs sont documentés ici dans AI Overview.

Chaque contrat IA détaille :
- input ;
- prompt context ;
- output JSON ;
- validation ;
- errors ;
- retries.

## 13.3 Prompt version obligatoire

Chaque appel IA structurant doit porter un `prompt_version`.

Exemple :

```txt
ai_prompt_version = observation_pipeline_v1
```

## 13.4 Pourquoi versionner

Le prompt versioning permet :
- rollback ;
- comparaison qualité ;
- debugging ;
- audit ;
- analyse des changements de comportement ;
- évolution contrôlée des schemas.

---

# 14. Logging policy

## 14.1 Pas de prompt/content en logs standards

Décision :

```txt
Pas de prompt/content IA en logs applicatifs standards.
```

## 14.2 Logs techniques uniquement

Logs autorisés :
- provider ;
- model ;
- latency ;
- status ;
- error_code ;
- token_count ;
- cost_estimate ;
- establishment_id ;
- correlation_id.

## 14.3 Pourquoi

Les prompts et contenus IA peuvent contenir :
- données opérationnelles sensibles ;
- données personnelles ;
- informations clients ;
- noms de personnes ;
- photos/audio transcrits ;
- contexte établissement.

## 14.4 Debug

Pour debug :
- utiliser AIUsageLog ;
- utiliser outputs structurés temporaires ;
- limiter accès admin/support ;
- éviter logs texte brut persistants.

---

# 15. Storage of AI outputs

## 15.1 Décision

Stockage technique limité des outputs IA structurés.

```txt
Structured AI outputs can be stored temporarily.
Full prompts are not stored long-term.
```

## 15.2 Rétention

Rétention MVP :

```txt
14 jours
```

Configurable.

## 15.3 Ce qui peut être stocké temporairement

- JSON output structuré ;
- validation errors ;
- provider metadata ;
- model ;
- prompt_version ;
- correlation_id.

## 15.4 Ce qui ne doit pas être stocké long terme

- prompts complets ;
- contenu brut complet non minimisé ;
- audio ;
- images ;
- données sensibles inutiles.

---

# 16. Privacy / RGPD principles

## 16.1 Minimisation stricte

Décision :

```txt
Envoyer uniquement le contexte nécessaire.
```

## 16.2 Audio

```txt
Pas d'audio conservé.
Audio supprimé après transcription.
```

## 16.3 Images

```txt
Pas d'image envoyée à l'IA au MVP.
```

Photos = contexte humain uniquement.

## 16.4 Prompt logging

```txt
Pas de logs prompts en clair.
```

## 16.5 Provider privacy

Utiliser dès que disponible :
- zero-retention ;
- no training ;
- DPA ;
- garanties contractuelles ;
- options enterprise/privacy.

## 16.6 Observation Pipeline

Observation Pipeline reçoit uniquement du texte validé.

```txt
No raw audio.
No image.
Validated text only.
```

---

# 17. Timeouts

## 17.1 Décision

Timeouts par domaine IA.

```txt
Transcription: 10s
Observation Pipeline: 20s
Onboarding: 60s
```

## 17.2 Pourquoi différencier

Chaque domaine a une temporalité différente :
- transcription : UX mobile rapide ;
- observation pipeline : async mais doit rester raisonnable ;
- onboarding : peut être plus long car setup initial.

## 17.3 Timeout behavior

Si timeout :
- log AIUsageLog failed ;
- retry selon domaine ;
- UX simplifiée ;
- admin/support peut voir failure.

---

# 18. Retry policy

## 18.1 Décision

Retry automatique limité.

```txt
Retry automatique limité.
Max attempts par type IA.
```

## 18.2 Failed state

Failed visible admin/support.

UX utilisateur simplifiée.

## 18.3 Max attempts

À détailler dans chaque contrat IA.

Recommandation générale :
- transcription : 1 retry utilisateur possible ;
- observation pipeline : retries backend limités ;
- onboarding : retry manuel ou automatique limité.

## 18.4 Pas de retry infini

Retry infini interdit.

Raisons :
- coût ;
- files bloquées ;
- provider instability ;
- risques de boucle.

---

# 19. Fallbacks

## 19.1 Fallback par domaine IA

```txt
Transcription → saisie texte
Onboarding → manuel + templates
Observation Pipeline → retry + failed admin + message UX simplifié
```

## 19.2 Transcription fallback

Si transcription échoue :

```txt
Utilisateur saisit le texte manuellement.
```

## 19.3 Onboarding fallback

Si onboarding IA échoue :

```txt
Retry
ou
manual fallback
ou
default templates
```

## 19.4 Observation Pipeline fallback

Si Observation Pipeline échoue :
- retry backend ;
- failed visible admin/support ;
- auteur voit message simplifié ;
- l'app globale continue.

---

# 20. Failure impact

## 20.1 Décision

IA failure ne bloque pas l'app globale.

Elle bloque seulement le flux concerné.

## 20.2 Par domaine

```txt
Onboarding
→ non activable sans structure validée

Observation
→ reste en analyse / failed

Transcription
→ fallback texte
```

## 20.3 UX simplifiée

L'utilisateur ne voit pas :
- JSON error ;
- provider error ;
- stacktrace ;
- token issue ;
- raw timeout detail.

Il voit un message métier simple.

---

# 21. Urgency

## 21.1 Décision MVP

L'IA ne décide pas et ne suggère pas l'urgence au MVP.

```txt
AI urgency decision = no
AI urgency suggestion = no MVP
```

## 21.2 Autorité urgence

L'urgence est contrôlée par :
- Manager ;
- Director ;
- Owner.

## 21.3 Pourquoi

L'urgence impacte :
- l'ordre du feed ;
- la perception terrain ;
- les futures notifications ;
- les escalades potentielles.

Elle doit donc rester humaine au MVP.

---

# 22. Permissions

## 22.1 Décision

L'IA ne décide jamais des permissions.

## 22.2 Detected domains

L'IA peut proposer :

```txt
detected_domains[]
```

Mais :

```txt
Backend applies RBAC.
```

## 22.3 Important

`detected_domains[]` influence :
- feed ;
- notifications ;
- actionability ;
- analytics.

Mais ce n'est pas l'IA qui décide des droits.

---

# 23. Actions

## 23.1 Décision MVP

L'IA ne crée pas d'Action au MVP.

```txt
AI does not create Actions MVP.
```

## 23.2 Post-MVP

Post-MVP possible :

```txt
AI suggests Actions
Human validates
Backend creates
```

## 23.3 Pourquoi

Action = responsabilité humaine assignée, exécutable et validable.

Créer automatiquement des Actions au MVP serait trop risqué.

---

# 24. Images

## 24.1 Décision MVP

Aucune image envoyée à l'IA au MVP.

```txt
No image sent to AI MVP.
```

## 24.2 Photos

Les photos servent :
- contexte humain ;
- preuve visuelle ;
- aide terrain.

Elles ne servent pas au pipeline IA au MVP.

---

# 25. Audio

## 25.1 Audio dans Transcription

L'audio est utilisé uniquement pour transcription.

## 25.2 Audio dans Observation Pipeline

Observation Pipeline ne reçoit jamais d'audio.

```txt
Observation Pipeline receives validated text only.
```

## 25.3 Audio retention

```txt
Audio deleted after transcription.
```

---

# 26. Events IA transverses

## 26.1 Events validés

```txt
AIRequestStarted
AIRequestSucceeded
AIRequestFailed
AIRequestRetried
```

## 26.2 Rôle

Ces events servent à :
- audit technique ;
- observabilité ;
- debug ;
- monitoring coût/performance ;
- corrélation avec events métier.

## 26.3 Ne remplacent pas les events métier

Les events IA transverses complètent les events métier.

Exemples :
- `ObservationProcessingStarted`
- `ObservationProcessingSucceeded`
- `OnboardingAIInterpretationStarted`
- `OnboardingAIInterpretationSucceeded`

---

# 27. Modèle technique recommandé

## 27.1 Provider interface

```rb
module Ai
  module Providers
    class Base
      def call(prompt:, schema:, metadata:)
        raise NotImplementedError
      end
    end
  end
end
```

## 27.2 Domain services

```txt
Ai::Onboarding::InterpretEstablishment
Ai::ObservationPipeline::AnalyzeObservation
Ai::Transcription::TranscribeAudio
```

## 27.3 Shared logging service

```txt
Ai::UsageLogger
```

## 27.4 Shared schema validation

```txt
Ai::SchemaValidator
```

## 27.5 Shared error handling

```txt
Ai::ErrorMapper
```

---

# 28. Backend constraints

## 28.1 No direct persistence from provider

Provider classes return raw structured response only.

Persistence belongs to domain services.

## 28.2 Schema validation before domain mutation

```txt
AI output
→ schema validation
→ domain validation
→ persistence
```

## 28.3 Establishment scope

Any AI request with establishment context must include:

```txt
establishment_id
correlation_id
ai_domain
```

## 28.4 Prompt version

Structuring AI requests must include:

```txt
prompt_version
```

---

# 29. Tests MVP

## 29.1 AI does not mutate DB

```txt
Given AI provider returns output
When provider call completes
Then no domain object is persisted by provider directly
```

## 29.2 JSON schema validation

```txt
Given invalid AI JSON
When backend validates output
Then output is rejected
And AIRequestFailed is emitted
```

## 29.3 AIUsageLog created

```txt
Given any AI call
When call completes
Then AIUsageLog is created with provider/model/status/latency/cost_estimate
```

## 29.4 No prompt in standard logs

```txt
Given AI call with sensitive content
When logs are inspected
Then prompt/content are absent from standard logs
```

## 29.5 Timeout handling

```txt
Given AI provider timeout
When timeout occurs
Then AIRequestFailed is emitted
And retry policy applies
```

## 29.6 Transcription fallback

```txt
Given transcription failure
When user returns to Observation form
Then user can type text manually
```

## 29.7 No image sent to AI

```txt
Given Observation with photos
When Observation Pipeline runs
Then images are not sent to AI provider
```

---

# 30. Décisions validées — index

| Décision | Statut |
|---|---:|
| IA = transcription + assistance + structuration + suggestion + routing | Validé |
| Backend = autorité métier finale | Validé |
| IA ne modifie jamais directement la DB | Validé |
| IA retourne proposition structurée | Validé |
| Backend valide, transforme, persiste | Validé |
| JSON schema strict pour outputs structurants | Validé |
| Backend valide toujours outputs IA | Validé |
| Validation humaine selon domaine | Validé |
| Onboarding validation humaine obligatoire | Validé |
| Transcription validée implicitement au submit | Validé |
| Observation Pipeline validation backend uniquement | Validé |
| AI docs séparés | Validé |
| Provider abstraction simple | Validé |
| Un provider actif MVP | Validé |
| Local/Ollama possible dev | Validé |
| Prod provider stable | Validé |
| Clé plateforme MVP | Validé |
| BYOK / clé établissement post-MVP | Validé |
| Tracking usage par établissement | Validé |
| AIUsageLog commun | Validé |
| Pas de prompt/content logs standards | Validé |
| Logs techniques uniquement | Validé |
| Stockage outputs structurés limité | Validé |
| Rétention 14 jours | Validé |
| Retry automatique limité | Validé |
| Failed visible admin/support | Validé |
| UX simplifiée | Validé |
| Timeouts 10s / 20s / 60s | Validé |
| Fallbacks par domaine | Validé |
| IA ne suggère pas urgence MVP | Validé |
| IA ne décide jamais permissions | Validé |
| IA ne crée pas d'Action MVP | Validé |
| Prompts séparés par domaine | Validé |
| Prompt version obligatoire | Validé |
| Minimisation RGPD stricte | Validé |
| Zero-retention / no training / DPA si disponible | Validé |
| Aucune image envoyée à l'IA MVP | Validé |
| Observation Pipeline reçoit uniquement texte validé | Validé |
| Audio supprimé après transcription | Validé |
| IA failure ne bloque pas l'app globale | Validé |
| Events IA transverses validés | Validé |
| Règle d'or validée | Validé |

---

# 31. Points à traiter dans les contrats détaillés

## 31.1 AI Onboarding Contract

À cadrer :
- input exact ;
- JSON schema modules/domains/units/vocabulary/routing hints ;
- validation humaine ;
- fallback templates ;
- relance IA post-activation.

## 31.2 AI Observation Pipeline Contract

À cadrer :
- input Observation ;
- checklist context ;
- establishment context ;
- active Signals context ;
- output candidates ;
- no_signal_created ;
- aggregation hints ;
- domain validation ;
- max 5 candidates ;
- max 4 domains.

## 31.3 AI Transcription Contract

À cadrer :
- audio lifecycle ;
- timeout ;
- retry ;
- language ;
- confidence ;
- edit/submit validation ;
- deletion audio ;
- fallback text.

---

# 32. Recommandation finale

Le domaine AI Overview est suffisamment cadré pour le MVP.

Décision centrale :

```txt
L'IA aide, structure et propose.
Le backend décide ce qui devient réel.
L'humain garde le contrôle des décisions structurantes et opérationnelles.
```

La prochaine étape logique est :

```txt
Houston_ai_observation_pipeline_contract.md
```

car c'est le contrat IA le plus critique pour la boucle métier Observation → Signal.
