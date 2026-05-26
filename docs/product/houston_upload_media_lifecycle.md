# Houston — Upload / Media Lifecycle

**Version:** v0.1  
**Date:** 2026-05-23  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Observation photos, temporary audio, uploads, storage, access, cleanup  
**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(15).txt`

**Documents liés :**
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_ai_transcription_contract.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_event_catalog.md`
- `Houston_notification_matrix.md`
- `Houston_rbac_permissions_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Upload / Media Lifecycle** de Houston pour le MVP.

Il définit :
- les types de médias MVP ;
- les règles photo Observation ;
- les règles audio temporaire ;
- les formats acceptés ;
- les limites de taille/durée ;
- la compression et normalisation ;
- les règles de stockage ;
- les signed URLs ;
- les règles d’accès RBAC ;
- les règles de TTL / cleanup ;
- le modèle de données ;
- les events ;
- les edge cases ;
- les tests fonctionnels attendus.

Ce domaine couvre uniquement :
- photos liées aux Observations ;
- audio temporaire de transcription.

Il ne couvre pas :
- documents PDF ;
- pièces jointes Action ;
- preuves avancées ;
- exports ;
- fichiers de configuration ;
- analyse IA image.

---

# 2. Principe central

```txt
Temporary upload first.
Validate and link on submit.
Private access only.
Cleanup is mandatory.
```

En français :

```txt
Uploader temporairement.
Valider et lier au submit.
Accès privé uniquement.
Nettoyage obligatoire.
```

---

# 3. Périmètre MVP

## 3.1 Media MVP

```txt
Media MVP
├── observation_photos
└── temporary_audio
```

## 3.2 Observation photos

Les photos Observation sont :
- optionnelles ;
- limitées à 3 par Observation ;
- uploadées temporairement avant submit ;
- liées à l’Observation au submit ;
- visibles via les Signals accessibles ;
- jamais envoyées à l’IA au MVP.

## 3.3 Temporary audio

L’audio est :
- temporaire ;
- utilisé uniquement pour transcription ;
- supprimé après succès ou échec final ;
- jamais transformé en ObservationMedia ;
- jamais envoyé au pipeline Observation.

---

# 4. Règles Observation / Photos

## 4.1 Photos optionnelles

```txt
Photos optionnelles.
Observation valide par texte ou transcription validée, pas par photo seule.
```

## 4.2 Photo-only interdite

```txt
Photo-only Observation interdite.
```

## 4.3 Max photos

```txt
Max 3 photos par Observation.
```

## 4.4 Photo temporaire avant submit

Une photo peut exister temporairement avant submit.

```txt
Photo peut exister temporairement avant submit.
Elle doit être liée à une Observation au submit ou supprimée par TTL.
```

## 4.5 No Observation detail page

Les Observations brutes ne sont pas visibles dans l’UI produit.

```txt
No direct Observation raw view in product UI.
```

---

# 5. Formats et limites photo

## 5.1 Formats acceptés

```txt
Photo formats MVP:
├── jpg
├── jpeg
├── png
└── heic
```

## 5.2 HEIC

```txt
HEIC accepté.
Conversion recommandée en JPEG pour affichage web/PWA.
Client-side preferred, backend fallback possible.
```

## 5.3 Compression client-side

```txt
Compression client-side avant upload.
Objectif : environ 1–2 MB par photo.
```

## 5.4 Taille max originale

```txt
Max original photo size = 10 MB.
```

## 5.5 Taille cible compressée

```txt
Compressed photo target = 1–2 MB.
```

## 5.6 Dimension max

```txt
Max long edge = 2048 px MVP.
```

## 5.7 Original non conservé

```txt
Ne pas conserver l’original MVP.
Conserver uniquement la version compressée/normalisée.
```

## 5.8 EXIF

```txt
Strip EXIF metadata before persistence.
```

Objectif :
- éviter fuite GPS ;
- réduire données personnelles ;
- minimiser les métadonnées.

---

# 6. Photos et IA

## 6.1 Décision MVP

```txt
Aucune image envoyée à l’IA.
Photos = contexte humain uniquement.
```

## 6.2 Conséquence

Le AI Observation Pipeline reçoit uniquement :
- texte validé ;
- contexte établissement ;
- contexte checklist éventuel ;
- active Signals pertinents.

Jamais :
- photo ;
- image thumbnail ;
- EXIF ;
- OCR image.

---

# 7. Visibilité des médias

## 7.1 Signal detail

```txt
Signal affiche les médias disponibles via Observations liées.
Signal ne montre pas les Observations brutes.
```

## 7.2 ObservationMedia

```txt
ObservationMedia belongs_to Observation.
Signal affiche les médias via linked Observations.
```

## 7.3 Auteur

```txt
Auteur voit les médias via Signal si Signal accessible.
Pas de page Observation detail.
```

## 7.4 RBAC

```txt
ObservationMedia visible via Signal accessible.
No direct Observation raw view in product UI.
```

---

# 8. Upload photo lifecycle

## 8.1 Flow standard

```txt
User selects photo
        ↓
Client validates format/size
        ↓
Client compresses/normalizes
        ↓
Temporary upload
        ↓
User submits Observation
        ↓
Backend validates temporary uploads
        ↓
Observation created
        ↓
ObservationMedia linked
        ↓
MediaLinkedToObservation event
```

## 8.2 Upload avant submit

```txt
Photos uploadées temporairement avant submit.
Liées à Observation au submit.
Orphelins nettoyés par TTL.
```

## 8.3 Upload async

```txt
Upload async avant submit pour photos et audio.
```

## 8.4 TTL photo temporaire

```txt
Temporary photo TTL = 24h.
```

---

# 9. Audio temporary lifecycle

## 9.1 TTL audio temporaire

```txt
Temporary audio TTL = 15 minutes.
```

## 9.2 Audio retention

```txt
Audio retention:
- delete after transcription success/final failure
- orphan TTL 15 minutes
```

## 9.3 Audio jamais durable

```txt
Audio ne devient jamais ObservationMedia.
Audio temporaire uniquement.
```

## 9.4 Flow audio

```txt
Audio recorded
        ↓
Temporary audio upload
        ↓
Transcription
        ↓
Text returned
        ↓
Audio deleted
        ↓
User edits/submits Observation text
```

---

# 10. Temporary uploads model

## 10.1 Table temporary_uploads

```txt
temporary_uploads
├── id
├── establishment_id
├── user_id
├── upload_type
├── storage_key
├── mime_type
├── file_size_bytes
├── status
├── expires_at
└── metadata
```

## 10.2 upload_type

```txt
upload_type:
├── observation_photo
└── transcription_audio
```

## 10.3 status

```txt
temporary_upload.status:
├── uploaded
├── linked
├── transcribing
├── deleted
├── expired
└── failed
```

## 10.4 Metadata examples

Photo metadata:
- width ;
- height ;
- normalized_mime_type ;
- compressed_size_bytes ;
- thumbnail_status.

Audio metadata:
- duration_ms ;
- provider_upload_reference if needed ;
- transcription_status.

---

# 11. ObservationMedia model

## 11.1 Table observation_media

```txt
observation_media
├── id
├── observation_id
├── establishment_id
├── uploaded_by_id
├── storage_key
├── mime_type
├── file_size_bytes
├── width
├── height
├── position
├── created_at
└── deleted_at
```

## 11.2 Position

```txt
ObservationMedia.position required.
```

Objectif :
- affichage stable ;
- respect de l’ordre choisi ;
- UX cohérente.

## 11.3 Audio exclu

```txt
Audio ne devient jamais ObservationMedia.
```

---

# 12. Stockage

## 12.1 Object storage

```txt
Private object storage S3-compatible.
Bucket privé.
No public files.
```

## 12.2 Bucket strategy

```txt
Private bucket unique.
Prefixes:
organizations/:organization_id/establishments/:establishment_id/...
```

## 12.3 Storage keys

```txt
storage_key example:
orgs/{organization_id}/establishments/{establishment_id}/observations/{observation_id}/media/{uuid}.jpg
temporary/{establishment_id}/{upload_type}/{uuid}
```

## 12.4 Original filename

```txt
Do not rely on original filename.
Generate UUID filenames.
Original filename optional sanitized, not displayed.
```

---

# 13. Access control

## 13.1 Private files

```txt
Private files.
Access via signed URLs short-lived after backend authorization.
```

## 13.2 Signed URL TTL

```txt
Signed URL TTL = 10 minutes.
```

## 13.3 RBAC check

```txt
Backend RBAC check before signed URL generation.
```

## 13.4 No public files

Aucun fichier média ne doit être public.

---

# 14. Thumbnails

## 14.1 Thumbnails MVP

```txt
Generate thumbnail MVP:
- original normalized/compressed
- thumbnail small
```

## 14.2 Generation async

```txt
Thumbnail generation async.
If thumbnail pending, UI can show placeholder.
```

## 14.3 Why

Les thumbnails réduisent :
- temps d’affichage ;
- bande passante mobile ;
- coût d’accès ;
- lenteur dans les feeds/détails.

---

# 15. Validation sécurité

## 15.1 Antivirus

```txt
MVP: MIME/extension/content validation stricte.
Antivirus scanning post-MVP unless simple managed option available.
```

## 15.2 Validation file type

```txt
Validate:
- extension allowlist
- declared MIME
- magic bytes/content type server-side
```

## 15.3 Rejet

Rejeter :
- extension non autorisée ;
- MIME incohérent ;
- magic bytes invalides ;
- taille > limite ;
- nombre de photos > 3 ;
- audio > 10 MB ou > 60s ;
- audio < 1s.

---

# 16. Upload strategy

## 16.1 MVP

```txt
MVP simple: backend-mediated upload.
```

## 16.2 Post-MVP

```txt
Post-MVP: direct-to-storage signed upload.
```

## 16.3 Pourquoi backend-mediated MVP

Plus rapide à builder :
- auth centralisée ;
- validation serveur simple ;
- moins de complexité S3 signed POST ;
- moins de surface bug mobile/PWA.

## 16.4 Limite

Backend-mediated upload peut devenir coûteux si volume élevé.  
Le direct-to-storage est à prévoir post-MVP.

---

# 17. Failure handling

## 17.1 Photo upload failed

```txt
Photo upload failed:
- afficher erreur sur photo
- retry possible
- suppression possible
- Observation peut être soumise sans photo si texte valide
```

## 17.2 Temporary photo expired

```txt
Expired temporary photo cannot be linked.
User must re-upload or submit without it.
```

## 17.3 Link media at submit

```txt
Observation submit links valid temporary uploads in transaction.
If media link fails due invalid upload, accept submit without photo.
```

## 17.4 Product warning

Ce choix évite de bloquer le signalement terrain, mais il faut éviter une perte silencieuse.

Recommandation UX :
- afficher que certaines photos n’ont pas été jointes ;
- permettre de continuer sans photo ;
- ne jamais faire croire qu’une photo a été envoyée si le link a échoué.

---

# 18. Suppression / retention

## 18.1 Suppression utilisateur

```txt
No standard user deletion after submit.
Admin/support soft delete with audit if needed.
```

## 18.2 Soft delete

```txt
ObservationMedia soft delete in DB.
Object can be hard-deleted by retention/admin policy.
```

## 18.3 Rétention photos validée

```txt
Delete photos when signal is resolved or canceled.
```

## 18.4 Alerte produit

Cette règle est stricte.

Impact :
- réduit le risque privacy ;
- réduit le stockage ;
- mais peut supprimer des preuves utiles après clôture.

Point à challenger plus tard :
- faut-il conserver les photos X jours après resolution/cancel pour audit ?
- faut-il différencier `resolved` et `canceled` ?
- faut-il garder metadata sans fichier ?

Pour le MVP, la décision validée est :

```txt
Delete photos when Signal is resolved or canceled.
```

## 18.5 Audio

```txt
Audio retention:
- delete after transcription success/final failure
- orphan TTL 15 minutes
```

---

# 19. Metadata

## 19.1 Safe metadata

```txt
Store safe metadata:
- image width/height
- audio duration_ms
- file_size_bytes
- mime_type
```

## 19.2 Metadata interdite

Ne pas stocker :
- EXIF complet ;
- GPS ;
- filename original brut affiché ;
- données device inutiles ;
- audio transcript dans media metadata.

---

# 20. Events

## 20.1 Events MVP validés

```txt
Events MVP:
MediaUploaded
MediaLinkedToObservation
MediaDeleted
TemporaryAudioUploaded
TemporaryAudioDeleted
OrphanMediaCleaned
```

## 20.2 Photo upload event

```txt
Use MediaUploaded with upload_type=observation_photo.
```

## 20.3 Audio event

```txt
Use TemporaryAudioUploaded for audio-specific lifecycle.
```

## 20.4 Notifications

```txt
No persisted notification for media upload success/failure.
UX inline + events/logs.
```

## 20.5 AIUsageLog

```txt
AIUsageLog only for transcription / AI calls.
Media upload has technical logs/events, not AIUsageLog.
```

---

# 21. Audit

## 21.1 User decision

```txt
Aucun audit
```

## 21.2 Practical interpretation

Aucun audit pour les vues normales des médias.

## 21.3 Admin/support

```txt
Admin/support media access allowed.
```

Recommandation technique minimale :
- accès admin/support doit être autorisé ;
- éviter l’accès libre ;
- les actions destructrices doivent rester traçables via events/logs.

## 21.4 Point à challenger

Même si l’arbitrage dit “aucun audit”, les suppressions admin/support devraient rester traçables pour éviter :
- suppression non expliquée ;
- perte de preuve ;
- problème support ;
- risque conformité.

Le document conserve donc :
- pas d’audit de consultation normale ;
- events/logs sur suppression via `MediaDeleted`.

---

# 22. Admin / Support access

## 22.1 Décision

```txt
Admin/support media access allowed.
```

## 22.2 Recommandation minimale

Admin/support access should be:
- authenticated ;
- authorized ;
- limited to support context ;
- not public ;
- visible in technical logs.

---

# 23. Image anonymization / watermark

## 23.1 Décision MVP

```txt
No image anonymization/watermark.
Privacy handled by access control + no public URLs + retention.
```

## 23.2 Post-MVP possible

Post-MVP :
- blur faces ;
- mask sensitive areas ;
- watermark ;
- AI-based image safety.

Non MVP.

---

# 24. Rate / size limits

## 24.1 Limites validées

```txt
MVP rate/size limits:
- max 3 photos per Observation
- max 10 MB original each
- max audio 10 MB / 60s
- optional daily upload abuse limit per user/establishment
```

## 24.2 Abuse limit

Recommandation :
- prévoir une limite configurable ;
- ne pas bloquer trop agressivement le pilote terrain ;
- logger les abus potentiels.

---

# 25. Encryption / transport

## 25.1 Encryption

```txt
Storage encryption at rest + TLS in transit.
```

## 25.2 App-level encryption

Post-MVP si requis par client ou sécurité avancée.

---

# 26. Environments

## 26.1 Décision

```txt
Separate buckets or prefixes per environment.
Prod isolated.
```

## 26.2 Recommandation

Minimum :
- prod séparé de dev/staging ;
- credentials séparés ;
- lifecycle policies séparées ;
- pas de données prod en dev.

---

# 27. API endpoints MVP

## 27.1 Upload temporary media

```txt
POST /api/v1/temporary_uploads
```

Body example:

```json
{
  "upload_type": "observation_photo",
  "file": "multipart"
}
```

Response:

```json
{
  "temporary_upload_id": "uuid",
  "upload_type": "observation_photo",
  "status": "uploaded",
  "expires_at": "datetime"
}
```

## 27.2 Delete temporary upload

```txt
DELETE /api/v1/temporary_uploads/:id
```

## 27.3 Get signed URL for media

```txt
POST /api/v1/observation_media/:id/signed_url
```

Requires RBAC check.

## 27.4 Submit Observation with media

```json
{
  "raw_text": "Fuite devant la chambre 312",
  "temporary_upload_ids": ["uuid1", "uuid2"]
}
```

---

# 28. Backend services recommandés

## 28.1 Media::TemporaryUploads::Create

Responsabilités :
- authenticate user ;
- validate establishment scope ;
- validate upload_type ;
- validate size ;
- validate MIME/extension/magic bytes ;
- normalize/compress if backend fallback ;
- store temporary file ;
- create temporary_upload ;
- emit MediaUploaded or TemporaryAudioUploaded.

## 28.2 Media::TemporaryUploads::Delete

Responsabilités :
- mark deleted ;
- delete object ;
- emit TemporaryAudioDeleted or MediaDeleted if relevant.

## 28.3 Media::TemporaryUploads::CleanupExpired

Responsabilités :
- find expired uploads ;
- delete objects ;
- mark expired/deleted ;
- emit OrphanMediaCleaned.

## 28.4 ObservationMedia::LinkTemporaryUploads

Responsabilités :
- validate temp uploads belong to user/establishment ;
- validate not expired ;
- validate upload_type observation_photo ;
- create ObservationMedia rows ;
- move/copy object if needed ;
- set position ;
- mark temporary_upload linked ;
- emit MediaLinkedToObservation.

## 28.5 Media::SignedUrl::Create

Responsabilités :
- RBAC check ;
- generate signed URL ;
- TTL 10 minutes.

## 28.6 Media::Thumbnails::GenerateJob

Responsabilités :
- generate small thumbnail ;
- update metadata ;
- handle failed thumbnail generation.

---

# 29. Edge cases

## 29.1 User uploads 4 photos

Reject 4th photo or prevent selection.

## 29.2 HEIC conversion fails

Options:
- retry backend conversion ;
- reject photo with actionable message ;
- allow user to upload different format.

## 29.3 Temporary upload expires before submit

Cannot link.  
User re-uploads or submits without photo.

## 29.4 Submit with invalid media ID

Ignore invalid media and submit without photo according to validated decision, but show clear UX warning.

## 29.5 Thumbnail generation fails

Media remains available.  
UI shows fallback/placeholder.

## 29.6 Signed URL expires

Frontend retries backend-mediated upload.

## 29.7 User loses access to Signal

Signed URL generation fails.  
Previously issued short-lived URL expires naturally.

## 29.8 Signal resolved/canceled

Photos linked to the Signal should be deleted according to validated retention decision.

## 29.9 Audio transcription fails

Audio deleted after final failure.

## 29.10 Cleanup job fails

Retry cleanup.  
Keep technical logs.

---

# 30. Tests fonctionnels MVP

## 30.1 Photo temporary upload

```txt
Given authenticated user
And valid jpg under 10 MB
When upload is requested
Then temporary_upload is created
And MediaUploaded is emitted
```

## 30.2 Invalid format rejected

```txt
Given unsupported file format
When upload is requested
Then upload is rejected
```

## 30.3 Max 3 photos

```txt
Given Observation draft already has 3 temporary photos
When user uploads fourth photo
Then upload is rejected
```

## 30.4 Observation submit links media

```txt
Given valid temporary photo upload
When Observation is submitted with temporary_upload_id
Then ObservationMedia is created
And temporary_upload status becomes linked
And MediaLinkedToObservation is emitted
```

## 30.5 Photo-only Observation rejected

```txt
Given user submits only photo and no valid text
When Observation submit occurs
Then submit is rejected
```

## 30.6 Expired upload not linked

```txt
Given expired temporary photo
When Observation submit tries to link it
Then media is not linked
And user can submit without photo if text is valid
```

## 30.7 Signed URL requires RBAC

```txt
Given user without access to Signal
When requesting media signed URL
Then request is rejected
```

## 30.8 Audio temporary deletion

```txt
Given audio transcription succeeds
When transcription completes
Then temporary audio object is deleted
And TemporaryAudioDeleted is emitted
```

## 30.9 EXIF stripped

```txt
Given photo with GPS EXIF
When media is persisted
Then stored media has no EXIF GPS metadata
```

## 30.10 Signal resolved deletes photos

```txt
Given Signal with linked ObservationMedia
When Signal becomes resolved
Then linked photo objects are deleted according to retention policy
```

---

# 31. Décisions validées — index

| Décision | Statut |
|---|---:|
| Domaine = photos Observation + audio temporaire | Validé |
| Media MVP = observation_photos + temporary_audio | Validé |
| Photo temporaire possible avant submit | Validé |
| Observation peut exister sans photo | Validé |
| Photo-only interdite | Validé |
| Max 3 photos par Observation | Validé |
| Formats jpg/jpeg/png/heic | Validé |
| HEIC accepté + conversion JPEG recommandée | Validé |
| Compression client-side | Validé |
| Max original photo size 10 MB | Validé |
| Cible compressée 1–2 MB | Validé |
| Max long edge 2048 px | Validé |
| Original photo non conservé | Validé |
| Strip EXIF | Validé |
| Aucune image envoyée à l’IA | Validé |
| Signal affiche médias via Observations liées | Validé |
| Signal ne montre pas Observations brutes | Validé |
| ObservationMedia belongs_to Observation | Validé |
| Temporary upload avant submit | Validé |
| Link au submit | Validé |
| Temporary photo TTL 24h | Validé |
| Temporary audio TTL 15 min | Validé |
| temporary_uploads table | Validé |
| upload_type observation_photo/transcription_audio | Validé |
| temporary_upload statuses validés | Validé |
| observation_media table | Validé |
| Audio jamais ObservationMedia | Validé |
| Private S3-compatible object storage | Validé |
| Private bucket, no public files | Validé |
| Bucket unique + prefixes tenant/type | Validé |
| Storage keys tenant-scoped + UUID | Validé |
| Signed URLs short-lived | Validé |
| Signed URL TTL 10 min | Validé |
| RBAC before signed URL | Validé |
| Media visible via accessible Signal | Validé |
| Auteur voit médias via Signal | Validé |
| No Observation detail page | Validé |
| Thumbnails MVP | Validé |
| Thumbnail async | Validé |
| Antivirus post-MVP | Validé |
| Strict extension/MIME/magic bytes validation | Validé |
| Backend-mediated upload MVP | Validé |
| Direct-to-storage post-MVP | Validé |
| Upload async avant submit | Validé |
| Upload failed retry/remove/submit sans photo | Validé |
| Expired temp photo cannot be linked | Validé |
| Invalid media link accepts submit without photo | Validé |
| ObservationMedia.position required | Validé |
| No standard user deletion after submit | Validé |
| Admin/support soft delete possible | Validé |
| ObservationMedia soft delete DB | Validé |
| Object hard delete by policy | Validé |
| Delete photos when Signal resolved/canceled | Validé |
| Audio deleted after transcription/final failure | Validé |
| Original filename not relied upon | Validé |
| Safe metadata stored | Validé |
| Media events validés | Validé |
| MediaUploaded with upload_type=observation_photo | Validé |
| TemporaryAudioUploaded audio lifecycle | Validé |
| No persisted media upload notification | Validé |
| No AIUsageLog for generic media | Validé |
| No audit for normal media views | Validé |
| Admin/support media access allowed | Validé |
| No anonymization/watermark MVP | Validé |
| Rate/size limits validés | Validé |
| Storage encryption at rest + TLS | Validé |
| Environments separated | Validé |
| Final principle validé | Validé |

---

# 32. Points à traiter ailleurs

## 32.1 Security / RGPD Baseline

À cadrer :
- rétention définitive ;
- traitement photos ;
- accès admin/support ;
- sous-traitants storage ;
- droit à suppression ;
- politique de minimisation.

## 32.2 Technical Architecture / ERD

À intégrer :
- `temporary_uploads` ;
- `observation_media` ;
- storage adapter ;
- cleanup jobs ;
- signed URL service.

## 32.3 API Contract

À cadrer :
- upload endpoints ;
- signed URL endpoint ;
- observation submit with temporary_upload_ids ;
- error codes upload.

## 32.4 Realtime / Feed

À cadrer :
- média thumbnail pending ;
- media linked updates ;
- feed refresh on Signal media update.

---

# 33. Recommandation finale

Le domaine Upload / Media Lifecycle est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Temporary upload first.
Validate and link on submit.
Private access only.
Cleanup is mandatory.
```

Le build doit maintenant s’appuyer sur :
- `temporary_uploads` ;
- `observation_media` ;
- object storage privé ;
- signed URLs ;
- compression client-side ;
- validation MIME/magic bytes ;
- cleanup TTL ;
- no public media ;
- no image sent to AI ;
- deletion audio immédiate ;
- deletion photos on Signal resolved/canceled ;
- tests de sécurité et lifecycle.
