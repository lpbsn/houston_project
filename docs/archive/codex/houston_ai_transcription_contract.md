# Houston — AI Transcription Contract

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Audio → Transcription → Observation text  
**Documents liés:**  
- `Houston_ai_overview.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_checklist_domain.md`
- `Houston_rbac_permissions_domain.md`

---

# 1. Objectif du document

Ce document formalise le contrat **AI Transcription** de Houston.

Il définit :
- le rôle de la transcription IA ;
- le lifecycle audio ;
- les limites de stockage ;
- les formats acceptés ;
- les limites de taille/durée ;
- le flow UX ;
- le contrat API ;
- les règles de validation ;
- les règles de suppression audio ;
- les logs / AIUsageLog ;
- les erreurs ;
- les events ;
- les services backend recommandés ;
- les tests fonctionnels attendus.

Ce document ne couvre pas l’analyse métier des Observations.  
L’analyse métier relève de `Houston_ai_observation_pipeline_contract.md`.

---

# 2. Principe central

```txt
Audio is temporary.
Transcription is editable.
Validated text becomes Observation.raw_text.
```

En français :

```txt
L’audio est temporaire.
La transcription est éditable.
Le texte validé devient Observation.raw_text.
```

---

# 3. Rôle de l’AI Transcription

## 3.1 Définition

AI Transcription transforme un audio temporaire en texte éditable.

```txt
Audio temporaire
        ↓
AI Transcription
        ↓
Texte éditable
        ↓
Utilisateur édite / valide implicitement
        ↓
Submit Observation
        ↓
Observation.raw_text
```

## 3.2 Ce que la transcription fait

La transcription :
- reçoit un audio temporaire ;
- produit un texte ;
- retourne ce texte au frontend ;
- permet à l’utilisateur de l’éditer ;
- alimente le champ texte de l’Observation.

## 3.3 Ce que la transcription ne fait pas

La transcription ne :
- crée pas d’Observation seule ;
- ne crée pas de Signal ;
- ne déclenche pas le pipeline Observation ;
- n’analyse pas le contenu métier ;
- ne décide pas de domains ;
- ne décide pas de routing ;
- ne persiste pas de donnée métier ;
- n’envoie pas d’audio au pipeline Observation.

---

# 4. Place dans le MVP

## 4.1 Transcription incluse MVP

Décision :

```txt
Transcription audio incluse dans le MVP.
```

## 4.2 Audio optionnel

L’audio est optionnel.

```txt
Input audio optional
Input text always available
```

## 4.3 Texte ou audio transcrit

Observation input :

```txt
texte
OU
audio transcrit validé
```

Important :

```txt
La transcription alimente le texte.
Ce ne sont pas deux inputs différents pour le pipeline IA Observation.
```

Le pipeline Observation reçoit uniquement :

```txt
Observation.raw_text
```

---

# 5. Validation utilisateur

## 5.1 Pas d’Observation sans validation utilisateur

L’audio ne peut pas créer une Observation sans validation utilisateur.

```txt
Audio → transcription → édition texte utilisateur → submit Observation
```

## 5.2 Validation implicite

La validation est implicite au submit.

```txt
Submit Observation = user validates final text
```

## 5.3 Pourquoi

Cette règle évite :
- faux Signals liés à une mauvaise transcription ;
- erreurs non corrigeables ;
- contradiction avec Observation non modifiable après submit ;
- mauvaise expérience terrain.

---

# 6. Lifecycle audio

## 6.1 Lifecycle validé

```txt
recording
        ↓
temporary upload / backend-controlled stream
        ↓
transcription
        ↓
editable text returned
        ↓
audio deleted after validated transcription
        ↓
Observation submit persists final text
```

## 6.2 Audio temporaire

L’audio est temporaire.

```txt
Audio is temporary.
```

## 6.3 Suppression audio

Décision :

```txt
Audio supprimé après transcription validée.
```

En cas d’échec final :

```txt
Audio supprimé après échec final.
```

## 6.4 Seule donnée persistable

Seule la transcription validée peut être persistée.

```txt
Observation.raw_text = texte validé soumis
```

---

# 7. Upload / transport audio

## 7.1 Pas d’appel provider direct frontend

Décision :

```txt
Pas d’appel provider direct depuis frontend.
```

## 7.2 Mode MVP

MVP autorise :

```txt
upload temporaire backend
OU
stream contrôlé backend vers provider
```

## 7.3 Pourquoi

Cette règle permet :
- protéger les clés provider ;
- contrôler les timeouts ;
- centraliser les logs ;
- appliquer les limites ;
- garantir establishment scope ;
- gérer cleanup audio ;
- tracer AIUsageLog.

---

# 8. Stockage temporaire audio

## 8.1 Stockage autorisé

Stockage temporaire autorisé uniquement le temps de transcrire.

```txt
Temporary audio storage allowed only during transcription.
```

## 8.2 Suppression après succès

Après transcription réussie :

```txt
delete audio immediately
```

## 8.3 Suppression après échec final

Après échec final :

```txt
delete audio immediately
```

## 8.4 Orphan audio TTL

Décision :

```txt
Orphan audio TTL = 15 minutes.
```

## 8.5 Cleanup job

Cleanup job obligatoire.

```txt
Temporary audio cleanup job required.
```

---

# 9. Formats / taille / durée

## 9.1 Formats acceptés MVP

```txt
webm
m4a
mp3
wav
```

## 9.2 Taille maximale

```txt
max_audio_file_size = 10 MB
```

## 9.3 Durée maximale

```txt
max_recording_duration = 60 seconds
```

## 9.4 Durée minimale

```txt
min_recording_duration = 1 second
```

Si durée < 1 seconde :

```txt
auto-cancel
```

## 9.5 Pourquoi ces limites

Ces limites contrôlent :
- coût IA ;
- abus ;
- latence ;
- UX mobile ;
- stockage temporaire ;
- complexité provider.

---

# 10. Timeout et retry

## 10.1 Timeout transcription

```txt
transcription_timeout = 10s
```

## 10.2 Timeout behavior

Si timeout :

```txt
TranscriptionFailed
error_code = transcription_timeout
```

UX :

```txt
Transcription impossible. Réessayez ou saisissez le texte.
```

## 10.3 Retry MVP

```txt
1 retry utilisateur possible
```

## 10.4 Pas de retry infini

```txt
No infinite automatic retry.
```

## 10.5 Pourquoi

La transcription est un flow interactif court.  
Un retry automatique lourd dégraderait :
- coût ;
- latence ;
- compréhension utilisateur ;
- stabilité UX.

---

# 11. Texte transcrit

## 11.1 Affichage

La transcription est affichée dans le champ texte.

```txt
transcription → text field
```

## 11.2 Édition

L’utilisateur peut éditer avant submit.

```txt
editable before submit
```

## 11.3 Persistence

La transcription est persistée uniquement comme `Observation.raw_text` au submit.

```txt
No business persistence before submit.
```

## 11.4 Pas de raw transcription séparée

Décision MVP :

```txt
Ne pas conserver la transcription brute séparément.
Conserver uniquement le texte validé soumis.
```

## 11.5 Confidence

Ne pas afficher la confidence à l’utilisateur.

```txt
confidence not displayed to user
```

Stockage technique possible dans AIUsageLog / metadata, sans usage métier MVP.

---

# 12. Longueur du texte transcrit

## 12.1 Texte court

La transcription peut être courte.

La validation finale se fait au submit Observation selon les règles Observation.

```txt
Observation validation owns final text validity.
```

Règle Observation :
- minimum 10 caractères ;
- exception possible si contexte checklist suffisant.

## 12.2 Texte trop long

Si transcription > 1000 caractères :

```txt
Afficher texte tronqué à 1000 caractères.
```

## 12.3 Alerte produit

La troncature automatique peut perdre de l’information.

Recommandation UX minimale :
- indiquer que le texte a été limité ;
- permettre à l’utilisateur de reformuler si besoin.

Message recommandé :

```txt
La transcription a été limitée à 1 000 caractères.
```

## 12.4 Pas de résumé automatique

Ne pas résumer automatiquement une transcription trop longue.

Pourquoi :
- cela mélange transcription et structuration ;
- risque de perte de sens ;
- responsabilité IA trop forte.

---

# 13. Langue et environnement audio

## 13.1 Langue par défaut

```txt
default language = fr-FR
```

## 13.2 Auto-detect

Auto-detect acceptable si le provider le gère.

UX reste en français.

## 13.3 Bruit / accent

MVP accepte l’environnement bruité via :
- provider robuste ;
- édition utilisateur ;
- retry utilisateur.

Pas de traitement audio avancé maison au MVP.

## 13.4 Contexte établissement

Décision MVP :

```txt
Pas de contexte établissement envoyé à la transcription.
```

La transcription ne reçoit pas :
- operational domains ;
- runtime vocabulary ;
- routing hints ;
- active Signals ;
- checklist context.

Post-MVP :
- vocabulary hints possibles si provider supporte.

---

# 14. Provider strategy

## 14.1 Service séparé

```txt
Ai::Transcription::TranscribeAudio
```

## 14.2 Provider abstraction

Transcription passe par provider abstraction.

```txt
Ai::Providers::Base
Ai::Providers::OpenAI
Ai::Providers::Ollama / Local optional dev
```

## 14.3 Contrat séparé

La transcription est séparée du pipeline Observation.

```txt
Transcription contract ≠ Observation Pipeline contract
```

## 14.4 Provider probable

Provider probable :

```txt
GPT Transcribe
```

Le choix exact reste implémentation/provider, mais le contrat produit reste indépendant.

---

# 15. API response contract

## 15.1 Réponse succès

```json
{
  "transcription": "Il y a une fuite devant la chambre 312",
  "language": "fr-FR",
  "duration_ms": 4200,
  "correlation_id": "uuid"
}
```

## 15.2 Empty transcription

Si transcription vide :

```txt
error_code = empty_transcription
```

UX :

```txt
Réessayez ou saisissez le texte.
```

## 15.3 Error response

```json
{
  "error": "transcription_failed",
  "error_code": "transcription_timeout",
  "correlation_id": "uuid"
}
```

Ne pas exposer les erreurs provider brutes.

---

# 16. UX states

## 16.1 States validés

```txt
recording
uploading
transcribing
transcription_ready
transcription_failed
```

## 16.2 recording

L’utilisateur enregistre.

## 16.3 uploading

L’audio est transféré vers le backend.

## 16.4 transcribing

Le backend/provider transcrit.

## 16.5 transcription_ready

Le texte est disponible et éditable.

## 16.6 transcription_failed

La transcription a échoué.

UX :

```txt
Transcription impossible. Réessayez ou saisissez votre signalement.
```

---

# 17. Cancel / replace / draft

## 17.1 Annulation

L’utilisateur peut annuler avant submit.

Backend doit cleanup audio temporaire.

## 17.2 Nouvel enregistrement

Un nouvel enregistrement remplace :
- l’audio précédent ;
- la transcription précédente.

Ancien audio supprimé.

## 17.3 Draft frontend

Le draft frontend peut contenir :
- texte transcrit édité.

Le draft frontend ne doit pas contenir :
- audio durable.

## 17.4 App fermée avant submit

Si app fermée avant submit :
- transcription peut être abandonnée ;
- audio temporaire nettoyé par TTL.

---

# 18. Offline

## 18.1 Transcription audio

```txt
Audio transcription requires online.
```

## 18.2 Offline MVP

Offline MVP peut supporter :
- texte local draft uniquement, si prévu.

Pas de transcription audio offline MVP.

---

# 19. Sécurité upload audio

## 19.1 Upload sécurisé obligatoire

```txt
Temporary audio upload sécurisé
```

Règles :
- MIME allowlist ;
- size limit ;
- duration limit ;
- authenticated user ;
- establishment scope ;
- cleanup TTL.

## 19.2 Scope

Chaque upload doit être relié à :
- user ;
- establishment ;
- correlation_id ;
- temporary upload id.

## 19.3 Rejet

Rejeter :
- format non supporté ;
- fichier trop gros ;
- durée trop longue ;
- durée trop courte ;
- utilisateur non authentifié ;
- établissement non accessible.

---

# 20. Permissions

## 20.1 Qui peut utiliser l’audio

Tous les rôles pouvant soumettre une Observation peuvent utiliser l’audio.

```txt
Owner
Director
Manager
Staff
```

## 20.2 Scope fonctionnel

Transcription uniquement dans le flow :

```txt
+Signaler / Observation
```

## 20.3 Hors MVP

Pas de transcription pour :
- commentaires ;
- Actions ;
- Chat ;
- checklist comments ;
- notes libres.

---

# 21. AIUsageLog

## 21.1 Log obligatoire

Chaque transcription crée un AIUsageLog.

```txt
ai_domain = transcription
```

## 21.2 Champs validés

```txt
AIUsageLog transcription
├── establishment_id
├── ai_domain=transcription
├── provider
├── model
├── status
├── latency_ms
├── input_audio_duration_ms
├── input_audio_size_bytes
├── cost_estimate
├── error_code
├── correlation_id
└── created_at
```

## 21.3 Pas de texte transcrit stocké

Ne pas stocker le texte transcrit dans les outputs IA techniques.

```txt
Store metadata only.
```

## 21.4 Pourquoi

Le texte final est déjà persisté dans `Observation.raw_text` seulement après submit.

Stocker une transcription brute séparée augmenterait :
- risque privacy ;
- surface RGPD ;
- confusion entre texte brut et texte validé.

---

# 22. Events

## 22.1 Events IA transverses

```txt
AIRequestStarted
AIRequestSucceeded
AIRequestFailed
AIRequestRetried
```

## 22.2 Events transcription

```txt
TranscriptionStarted
TranscriptionSucceeded
TranscriptionFailed
TranscriptionAudioDeleted
```

## 22.3 Event correlation

Tous les events doivent inclure :
- correlation_id ;
- establishment_id ;
- user_id ;
- temporary_audio_id si applicable.

## 22.4 TranscriptionAudioDeleted

Émis après suppression audio temporaire.

Si cleanup échoue :

```txt
error_code = cleanup_failed
```

Admin/support visible.

---

# 23. Error codes

## 23.1 Codes validés

```txt
audio_too_short
audio_too_large
unsupported_audio_format
transcription_timeout
provider_unavailable
empty_transcription
invalid_audio
upload_failed
cleanup_failed
unknown_error
```

## 23.2 Mapping UX

Tous les codes doivent être mappés vers des messages simples.

Message générique validé :

```txt
Transcription impossible. Réessayez ou saisissez votre signalement.
```

## 23.3 Pas d’erreur provider brute

Ne pas exposer :
- stacktrace ;
- provider raw error ;
- détails token/API ;
- timeout technique brut.

---

# 24. Privacy / information utilisateur

## 24.1 Mention claire

Afficher une mention claire :

```txt
L’audio sert uniquement à générer le texte et n’est pas conservé.
```

## 24.2 Pas de microcopy supplémentaire obligatoire

Décision :

```txt
Pas de microcopy additionnelle obligatoire dans le flow.
```

## 24.3 Micro-permission navigateur

Le navigateur gère la permission microphone.

L’UI doit rester claire sur :
- pourquoi le micro est demandé ;
- ce qui est fait avec l’audio ;
- la possibilité de saisir du texte à la place.

---

# 25. API endpoints MVP

## 25.1 Upload temporary audio

```txt
POST /api/v1/transcriptions/audio_uploads
```

Response:

```json
{
  "temporary_audio_id": "uuid",
  "correlation_id": "uuid"
}
```

## 25.2 Transcribe audio

```txt
POST /api/v1/transcriptions
```

Body:

```json
{
  "temporary_audio_id": "uuid"
}
```

Response:

```json
{
  "transcription": "Il y a une fuite devant la chambre 312",
  "language": "fr-FR",
  "duration_ms": 4200,
  "correlation_id": "uuid"
}
```

## 25.3 Delete temporary audio

```txt
DELETE /api/v1/transcriptions/audio_uploads/:id
```

Can be called:
- after transcription success ;
- after cancel ;
- before replacement recording.

---

# 26. Backend services recommandés

## 26.1 Transcriptions::UploadAudio

Responsabilités :
- authenticate user ;
- validate establishment scope ;
- validate MIME ;
- validate size ;
- store temporary audio ;
- assign TTL ;
- return temporary_audio_id.

## 26.2 Transcriptions::Transcribe

Responsabilités :
- load temporary audio ;
- validate duration ;
- call AI transcription service ;
- enforce timeout ;
- create AIUsageLog ;
- return editable text ;
- delete audio after success ;
- emit events.

## 26.3 Ai::Transcription::TranscribeAudio

Responsabilités :
- call provider ;
- normalize provider response ;
- return transcription payload ;
- map provider errors.

## 26.4 Transcriptions::DeleteTemporaryAudio

Responsabilités :
- delete object storage audio ;
- emit TranscriptionAudioDeleted ;
- handle cleanup failure.

## 26.5 Transcriptions::CleanupOrphansJob

Responsabilités :
- delete temporary audio older than TTL ;
- emit cleanup events/logs ;
- ensure no orphan audio remains.

---

# 27. Data model recommandé

## 27.1 temporary_audio_uploads

```txt
temporary_audio_uploads
├── id UUID
├── establishment_id UUID
├── user_id UUID
├── storage_key string
├── mime_type string
├── file_size_bytes integer
├── duration_ms integer nullable
├── status enum
│   ├── uploaded
│   ├── transcribing
│   ├── transcribed
│   ├── failed
│   └── deleted
├── correlation_id UUID
├── expires_at datetime
├── deleted_at datetime nullable
├── created_at
└── updated_at
```

## 27.2 No transcription table MVP

Ne pas créer de table métier `transcriptions`.

Le texte transcrit :
- retourne au frontend ;
- devient `Observation.raw_text` uniquement si l’utilisateur submit.

## 27.3 AIUsageLog

Voir section AIUsageLog.

---

# 28. Edge cases

## 28.1 Audio < 1s

```txt
Reject / auto-cancel
error_code = audio_too_short
```

## 28.2 Audio > 60s

```txt
Reject
```

## 28.3 Audio > 10 MB

```txt
Reject
error_code = audio_too_large
```

## 28.4 Unsupported format

```txt
Reject
error_code = unsupported_audio_format
```

## 28.5 Provider timeout

```txt
TranscriptionFailed
error_code = transcription_timeout
UX retry/text fallback
```

## 28.6 Empty transcription

```txt
TranscriptionFailed
error_code = empty_transcription
UX retry/text fallback
```

## 28.7 User cancels

```txt
Delete temporary audio
Do not persist text
```

## 28.8 User records again

```txt
Delete previous temporary audio
Replace transcription text
```

## 28.9 App closes

```txt
TTL cleanup deletes temporary audio
```

## 28.10 Transcription > 1000 chars

```txt
Truncate displayed text to 1000 chars
Show notice
```

## 28.11 Transcription short

Allow display.  
Final submit validation belongs to Observation.

## 28.12 Cleanup fails

```txt
error_code = cleanup_failed
admin/support visible
retry cleanup job
```

---

# 29. Tests fonctionnels MVP

## 29.1 Valid audio transcribed

```txt
Given authenticated user
And valid temporary audio
When transcription is requested
Then transcription text is returned
And audio is deleted
And AIUsageLog is created
```

## 29.2 No Observation created by transcription

```txt
Given transcription succeeds
When user does not submit Observation
Then no Observation is created
```

## 29.3 Submit persists final edited text

```txt
Given transcription text returned
And user edits text
When user submits Observation
Then Observation.raw_text equals edited text
```

## 29.4 Audio too short

```txt
Given audio duration < 1 second
When upload/transcription requested
Then request is rejected
And error_code = audio_too_short
```

## 29.5 Audio too large

```txt
Given audio file > 10 MB
When upload requested
Then request is rejected
And error_code = audio_too_large
```

## 29.6 Unsupported format

```txt
Given unsupported MIME type
When upload requested
Then request is rejected
```

## 29.7 Timeout fallback

```txt
Given provider timeout
When transcription requested
Then TranscriptionFailed is emitted
And user can retry or type text
```

## 29.8 Empty transcription

```txt
Given provider returns empty text
When transcription completes
Then TranscriptionFailed with empty_transcription
And user can retry or type text
```

## 29.9 New recording replaces previous

```txt
Given user has temporary audio A
When user records audio B
Then audio A is deleted
And only audio B remains
```

## 29.10 Draft contains no audio

```txt
Given user closes app after transcription_ready
When draft is stored
Then only text may be stored
And audio is not stored durably
```

## 29.11 Offline audio transcription rejected

```txt
Given user offline
When user tries audio transcription
Then user is invited to type text
```

## 29.12 No raw transcription stored

```txt
Given transcription succeeds
When inspecting AI technical output storage
Then transcribed text is not stored there
```

---

# 30. Décisions validées — index

| Décision | Statut |
|---|---:|
| AI Transcription = audio temporaire vers texte éditable | Validé |
| Ne crée pas d’Observation seule | Validé |
| Transcription audio incluse MVP | Validé |
| Audio optionnel, texte toujours disponible | Validé |
| Observation input = texte ou audio transcrit validé | Validé |
| Pipeline Observation reçoit seulement texte validé | Validé |
| Audio → transcription → édition texte → submit Observation | Validé |
| Validation implicite au submit | Validé |
| Audio temporaire | Validé |
| Audio supprimé après transcription validée | Validé |
| Texte validé seul persistable | Validé |
| Pas d’appel provider direct frontend | Validé |
| Upload/stream backend contrôlé | Validé |
| Stockage audio temporaire uniquement pendant transcription | Validé |
| Suppression après succès ou échec final | Validé |
| Orphan audio TTL 15 minutes | Validé |
| Cleanup job obligatoire | Validé |
| Formats webm/m4a/mp3/wav | Validé |
| Max audio size 10 MB | Validé |
| Max duration 60s | Validé |
| Min duration 1s | Validé |
| Timeout 10s | Validé |
| Timeout → transcription_failed | Validé |
| 1 retry utilisateur possible | Validé |
| Transcription éditable avant submit | Validé |
| Persistence uniquement au submit Observation | Validé |
| Pas de raw transcription séparée | Validé |
| Confidence non affichée utilisateur | Validé |
| Langue par défaut fr-FR | Validé |
| Pas de traitement audio avancé maison | Validé |
| Pas de contexte établissement envoyé transcription MVP | Validé |
| Service Ai::Transcription::TranscribeAudio | Validé |
| Provider probable GPT Transcribe | Validé |
| AIUsageLog pour chaque transcription | Validé |
| Metadata audio non sensible | Validé |
| Pas de texte transcrit en output IA technique | Validé |
| API response validée | Validé |
| Empty transcription failed | Validé |
| Validation longueur finale au submit Observation | Validé |
| >1000 chars affiché tronqué à 1000 | Validé |
| UX states validés | Validé |
| Annulation avant submit possible | Validé |
| Nouvel enregistrement remplace précédent | Validé |
| Pas d’audio draft durable | Validé |
| App fermée → abandon + TTL cleanup | Validé |
| Audio transcription online only | Validé |
| Upload sécurisé | Validé |
| Tous rôles Observation peuvent utiliser audio | Validé |
| Transcription seulement dans +Signaler / Observation | Validé |
| Events transcription validés | Validé |
| Error codes validés | Validé |
| Message UX échec validé | Validé |
| Mention audio non conservé | Validé |
| Pas de microcopy additionnelle obligatoire | Validé |
| Principe final validé | Validé |

---

# 31. Points à traiter ailleurs

## 31.1 Upload / Media Lifecycle

À cadrer :
- stockage temporaire object storage ;
- signed URLs ;
- cleanup global ;
- media security ;
- photos Observation.

## 31.2 AI Provider Implementation

À cadrer :
- provider exact ;
- modèle exact ;
- pricing ;
- API limits ;
- fallback provider ;
- SDK implementation.

## 31.3 Security / RGPD

À cadrer :
- mentions légales ;
- consentement micro ;
- DPA provider ;
- zero-retention ;
- logs sécurité.

## 31.4 Frontend PWA

À cadrer :
- microphone permissions ;
- iOS Safari behavior ;
- recording component ;
- offline behavior ;
- local draft rules.

---

# 32. Recommandation finale

Le contrat AI Transcription est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Audio is temporary.
Transcription is editable.
Validated text becomes Observation.raw_text.
```

Le build doit maintenant s’appuyer sur :
- audio optionnel ;
- texte toujours disponible ;
- backend-controlled upload/stream ;
- suppression audio rapide ;
- TTL 15 min ;
- formats/size/duration stricts ;
- transcription éditable ;
- persistence uniquement au submit ;
- no raw transcription storage ;
- AIUsageLog metadata-only ;
- UX fallback texte ;
- transcription limitée au flow +Signaler / Observation.

La prochaine étape logique est :

```txt
Houston_ai_onboarding_contract.md
```

ou, si tu veux sortir du périmètre IA :

```txt
Houston_event_catalog.md
```
