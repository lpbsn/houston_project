# Houston — Security / RGPD Baseline

**Version:** v0.1  
**Date:** 2026-05-24  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — sécurité, privacy, RGPD, rétention, accès, logs, backups, sous-traitants  
**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(16).txt`

**Important :** ce document est une baseline produit/tech. Il ne remplace pas une validation juridique, un DPA, une politique de confidentialité ou une analyse DPO/avocat.

---

# 1. Objectif du document

Ce document formalise la baseline **Security / RGPD** de Houston pour le MVP.

Il définit :
- les rôles RGPD produit ;
- les catégories de données ;
- les principes de minimisation ;
- les règles de visibilité ;
- les règles IA / logs / prompts ;
- l’hébergement ;
- l’authentification ;
- l’autorisation backend ;
- l’accès admin/support ;
- les règles de rétention ;
- les sauvegardes ;
- le chiffrement ;
- la gestion des secrets ;
- les règles API / CORS / realtime / push ;
- le process incident ;
- les règles dev/staging/prod ;
- les sous-traitants ;
- les principes PWA.

---

# 2. Principe central

```txt
Privacy by design.
Least privilege.
Minimal data.
Controlled retention.
Secure by default.
```

---

# 3. Statut du document

```txt
Security / RGPD Baseline = règles produit/tech minimales de sécurité, privacy et conformité pour le MVP.
```

Ce document n’est pas :
- un DPA ;
- une politique de confidentialité ;
- un contrat client ;
- une analyse d’impact complète ;
- un avis juridique ;
- une preuve de conformité.

Avant tout pilote client réel :
- DPA / contrat de sous-traitance ;
- subprocessors list ;
- registre de traitement minimal ;
- DPIA screening ;
- politique de confidentialité ;
- validation juridique/DPO si nécessaire.

---

# 4. Rôles RGPD

## 4.1 Données opérationnelles

```txt
Client établissement = responsable de traitement pour les données opérationnelles.
Houston = sous-traitant pour ce traitement.
```

## 4.2 Données plateforme

```txt
Houston = responsable de traitement pour :
- gestion compte plateforme
- sécurité
- facturation
- support
- logs techniques nécessaires
```

## 4.3 DPA obligatoire

```txt
DPA / contrat de sous-traitance requis avant pilote client réel.
```

---

# 5. Catégories de données

```txt
Data categories:
- user account data
- membership / roles / domains
- operational content
- observations textuelles
- photos
- comments
- notifications
- technical logs
- AI metadata
- audit/events
```

## 5.1 Observations

```txt
Observations may contain personal data accidentally.
Apply minimization, access control, retention, no raw exposure.
```

## 5.2 Photos

```txt
Photos = potentially sensitive operational media.
Private storage + signed URLs + retention + no AI image analysis MVP.
```

---

# 6. Minimisation

```txt
Collect only what is needed for operational workflow.
```

Ne pas collecter ou exposer inutilement :
- adresse exacte si non nécessaire ;
- données personnelles des clients finaux ;
- audio durable ;
- images pour IA ;
- prompts IA en clair ;
- texte brut Observation dans events/notifications/logs ;
- fichiers originaux si version compressée suffisante ;
- EXIF des photos.

```txt
Raw Observations not visible in product UI.
Admin/database access only.
```

---

# 7. IA et données

## 7.1 Images

```txt
No image sent to AI MVP.
```

## 7.2 Audio

```txt
Observation Pipeline receives validated text only.
Audio deleted after transcription.
```

## 7.3 Prompt/content logs

```txt
No clear prompt/content logs.
Only technical AI metadata.
```

## 7.4 Outputs IA structurés

```txt
Structured AI outputs retained 14 days max.
No full prompt logs.
```

## 7.5 Provider IA

```txt
AI provider allowed only with contractual/privacy safeguards:
- DPA
- no training / zero retention if available
- transfer safeguards when required
```

## 7.6 Clé API IA

```txt
AI platform key stored in secure environment/secret manager.
BYOK post-MVP.
Clé par établissement post-MVP.
```

---

# 8. Hébergement et localisation

```txt
Host application, DB, object storage and backups in France/EU.
```

```txt
Separate buckets or prefixes per environment.
Prod isolated.
```

```txt
No production personal data in dev/staging.
Use synthetic/anonymized data.
```

```txt
Use synthetic data for dev/test/demo.
```

---

# 9. Registre et DPIA

## 9.1 Registre de traitements minimal

```txt
Maintain a minimal processing registry:
- purpose
- data categories
- legal basis/client role
- retention
- processors
- security measures
```

## 9.2 DPIA screening

```txt
Perform DPIA screening before pilot.
Full DPIA if risk criteria are met.
```

Le DPIA screening doit vérifier notamment :
- traitement de données sensibles accidentelles ;
- photos terrain ;
- suivi potentiel d’employés ;
- volume important ;
- contexte client final ;
- IA impliquée dans routing/signalisation.

---

# 10. Authentification

## 10.1 Auth token-based

```txt
Auth token-based:
- short-lived access token
- refresh token rotation
- revoke on logout / membership deactivation
```

## 10.2 MFA

```txt
MFA non MVP.
```

Point à réévaluer pour Owner/Admin/support avant pilote réel.

## 10.3 Password security

```txt
Use proven password hashing.
No homemade crypto.
Support password reset securely.
```

## 10.4 CSRF

```txt
If bearer token auth: protect token storage and CORS.
```

Si cookie-based auth plus tard :
- CSRF obligatoire ;
- cookies secure/httpOnly/sameSite à cadrer.

---

# 11. Autorisation

```txt
Backend authorization required for read, write, signed URLs, notifications, realtime channels.
```

```txt
All access scoped by EstablishmentMembership:
- establishment_id
- role
- operational_domains
- status
```

Le frontend peut masquer des éléments, mais le backend reste la seule frontière de sécurité.

```txt
Signed URL TTL = 10 minutes.
RBAC required before generation.
```

```txt
Realtime channels must enforce:
- authenticated user
- establishment membership
- role/domain visibility
```

---

# 12. Admin / Support access

```txt
Admin/support access:
- explicit role
- least privilege
- technical logging
- destructive actions audited
```

```txt
MVP admin/support console:
- read technical statuses
- failed jobs
- AI usage logs
- upload cleanup
- no arbitrary data browsing by default
```

```txt
Production DB access:
- least privilege
- named accounts
- logged
- time-limited when possible
```

```txt
No audit for normal media views.
```

Point de vigilance :
- les suppressions et actions destructrices doivent être tracées ;
- l’accès admin/support doit rester contrôlé même si toutes les vues normales ne sont pas auditées.

---

# 13. Logs

## 13.1 Logs autorisés

```txt
Allowed logs:
- ids
- event_type
- error_code
- latency
- status
- provider/model
- correlation_id
```

## 13.2 Logs interdits

```txt
Forbidden:
- raw Observation text
- full comments
- audio
- photos
- secrets/tokens
```

## 13.3 Rétention

```txt
Technical logs retention = 30 days MVP.
```

```txt
Security/audit logs retention = 12 months MVP.
```

---

# 14. Rétention des données

```txt
Business/audit events retention = 24 months MVP.
```

```txt
Notifications retention = 90 days.
Delivery logs = 30 days.
```

```txt
MVP current decision: Delete photos when Signal is resolved or canceled.
```

```txt
Audio deleted after transcription success/final failure.
Orphan audio TTL = 15 min.
```

```txt
Structured AI outputs retained 14 days max.
```

## 14.1 Point à challenger

La suppression des photos dès `Signal resolved/canceled` est privacy-first, mais peut réduire la capacité :
- d’audit ;
- de support ;
- de vérification post-incident ;
- de contestation ou analyse après clôture.

Décision MVP conservée :

```txt
Delete photos when Signal is resolved or canceled.
```

---

# 15. Backups

```txt
PostgreSQL backups:
- WAL / PITR
- daily full backup
- encrypted
- restore tests
```

```txt
MVP backup retention:
- 14 days fast restore
- 30 days standard
- cold longer retention post-MVP/client policy
```

```txt
Deleted media may remain in encrypted backups until backup retention expires.
Document this clearly.
```

Restore tests :
- test manuel mensuel recommandé ;
- procédure restore documentée.

---

# 16. Chiffrement et transport

```txt
Encryption at rest:
- database
- object storage
- backups
```

```txt
TLS in transit everywhere.
```

---

# 17. Secrets management

```txt
No secrets in Git.
Use environment secrets / managed secret store.
Rotate compromised secrets.
```

```txt
Storage credentials backend-only.
Signed URLs generated after authorization.
```

Secrets à protéger :
- DB credentials ;
- JWT/signing keys ;
- AI API key ;
- object storage credentials ;
- email provider keys ;
- push provider keys ;
- monitoring/logging tokens.

---

# 18. Rate limiting

```txt
Rate limit:
- login/password reset
- uploads
- AI transcription
- Observation submit
- signed URL generation
```

Objectifs :
- limiter brute force ;
- limiter spam uploads ;
- limiter coûts IA ;
- limiter abus signed URLs ;
- limiter floods Observations.

---

# 19. API / CORS / Frontend security

```txt
CORS allowlist per environment.
No wildcard in production.
```

```txt
No raw HTML user-generated content.
Escape/sanitize all displayed text.
```

```txt
Server-side file validation required.
```

```txt
Push payload minimal:
- notification_id
- short title/body non-sensitive
- subject_type/id
No raw content.
```

---

# 20. Upload security

Uploads validés côté serveur :
- extension ;
- MIME ;
- magic bytes ;
- taille ;
- durée audio ;
- type attendu ;
- scope utilisateur/établissement.

```txt
Signed URL TTL = 10 minutes.
RBAC required before generation.
```

---

# 21. Incident response

## 21.1 Process MVP

```txt
MVP incident process:
- detect
- contain
- assess personal data breach
- notify client if needed
- document
```

## 21.2 Violation de données

```txt
As processor, Houston notifies client/controller without undue delay when breach suspected.
Client handles regulatory notifications unless Houston is controller for that processing.
```

## 21.3 Documentation

Tout incident doit être documenté :
- date ;
- nature ;
- données concernées ;
- périmètre ;
- cause ;
- actions de containment ;
- actions correctives ;
- notification client si applicable.

---

# 22. Export / deletion / DSAR

```txt
MVP: manual export support process.
Post-MVP: self-service export.
```

```txt
MVP: controlled offboarding/deletion procedure.
Define what is deleted, anonymized, retained for legal/security.
```

```txt
MVP: manual DSAR process with client/controller coordination.
```

Le process doit préciser :
- qui reçoit ;
- qui valide ;
- qui extrait ;
- qui supprime/anonymise ;
- qui répond ;
- quels délais.

---

# 23. Sous-traitants

```txt
Maintain subprocessors list:
- hosting
- database/storage
- AI provider
- email provider
- push provider
- monitoring/logging
```

Pour chaque sous-traitant :
- nom ;
- service ;
- localisation ;
- type de données ;
- rôle ;
- garanties contractuelles ;
- DPA/SCC si applicable ;
- contact/support/security page.

---

# 24. Monitoring

```txt
MVP monitoring:
- auth failures spikes
- upload failures
- AI failures
- cleanup failures
- job queue failures
- high error rates
```

Alertes minimales :
- jobs critiques en échec ;
- cleanup audio/media échoué ;
- taux d’erreur API élevé ;
- AI provider unavailable ;
- spike login failed ;
- storage upload failure.

---

# 25. PWA security

```txt
PWA security:
- avoid storing sensitive content offline
- no durable audio local
- secure token strategy
- minimal push payload
```

Ne pas stocker durablement :
- audio ;
- photos ;
- raw Observations ;
- full comments ;
- tokens non protégés.

Les drafts frontend doivent rester minimaux et contrôlés.

---

# 26. Modèle de contrôle par domaine

Tout accès à un objet doit vérifier :
- user authenticated ;
- membership active ;
- establishment match ;
- role ;
- operational_domains si applicable ;
- object visibility ;
- subject status si nécessaire.

```txt
Backend authorization required for:
- read
- write
- signed URLs
- notifications
- realtime channels
```

---

# 27. Technical implementation recommendations

## 27.1 Services recommandés

```txt
Security::Authorize
Security::RateLimit
Security::AuditLog
Security::IncidentReport
Security::Retention::Cleanup
Security::Secrets
Security::CorsPolicy
```

## 27.2 Policies

Recommandé :
- `SignalPolicy`
- `ActionPolicy`
- `ChecklistPolicy`
- `ObservationMediaPolicy`
- `NotificationPolicy`
- `AdminSupportPolicy`

## 27.3 Retention jobs

Jobs nécessaires :
- delete expired temporary uploads ;
- delete audio after transcription ;
- delete AI structured outputs after 14 days ;
- delete notification deliveries after 30 days ;
- delete notifications after 90 days ;
- delete technical logs after 30 days ;
- apply media deletion when Signal resolved/canceled.

---

# 28. Tests fonctionnels MVP

## 28.1 Raw Observation not exposed

```txt
Given Observation exists
When product UI/API fetches Signal detail
Then Observation.raw_text is not returned
```

## 28.2 No image sent to AI

```txt
Given Observation has photos
When AI Observation Pipeline runs
Then image data is not included in AI payload
```

## 28.3 No prompt logs

```txt
Given AI call runs
When app logs are inspected
Then prompt/content are absent
And only metadata is logged
```

## 28.4 RBAC signed URL

```txt
Given user has no access to Signal
When user requests media signed URL
Then request is denied
```

## 28.5 Push payload minimal

```txt
Given ActionAssigned notification
When push payload is generated
Then no raw operational content is included
```

## 28.6 Membership deactivated

```txt
Given user membership is deactivated
When user tries API access
Then access token/refresh is revoked or access denied
```

## 28.7 Rate limit upload

```txt
Given user exceeds upload limits
When user uploads more files
Then request is rate-limited
```

## 28.8 Dev environment data

```txt
Given dev/staging environment
When database is seeded
Then data is synthetic/anonymized
```

## 28.9 Retention cleanup

```txt
Given AI structured output older than 14 days
When cleanup runs
Then output is deleted
```

## 28.10 Incident process documented

```txt
Given suspected personal data breach
When incident is opened
Then containment, assessment, client notification decision, and documentation are recorded
```

---

# 29. Décisions validées — index

| Décision | Statut |
|---|---:|
| Baseline produit/tech sécurité/RGPD MVP | Validé |
| Client établissement responsable de traitement opérationnel | Validé |
| Houston sous-traitant opérationnel | Validé |
| Houston responsable plateforme/sécurité/billing/support/logs nécessaires | Validé |
| DPA requis avant pilote réel | Validé |
| Data categories validées | Validé |
| Observations peuvent contenir données personnelles accidentelles | Validé |
| Photos potentiellement sensibles | Validé |
| Minimisation stricte | Validé |
| Raw Observations non visibles UI | Validé |
| Pas d’image envoyée à l’IA | Validé |
| Audio jamais envoyé au pipeline Observation | Validé |
| No clear prompt/content logs | Validé |
| Structured AI outputs 14 jours max | Validé |
| Hébergement app/DB/storage/backups France/UE | Validé |
| Provider IA avec DPA/garanties/no-training/zero-retention si dispo | Validé |
| Registre de traitements minimal | Validé |
| DPIA screening avant pilote | Validé |
| Auth token-based + refresh rotation | Validé |
| MFA non MVP | Validé |
| Password hashing éprouvé | Validé |
| Backend authorization partout | Validé |
| Access scoped by EstablishmentMembership | Validé |
| Admin/support access least privilege | Validé |
| Destructive admin actions audited | Validé |
| No audit normal media views | Validé |
| Logs techniques sans contenu sensible | Validé |
| Technical logs retention 30 jours | Validé |
| Security/audit logs 12 mois | Validé |
| Business/audit events 24 mois | Validé |
| Notifications 90 jours, delivery logs 30 jours | Validé |
| Photos deleted when Signal resolved/canceled | Validé |
| Audio deleted after transcription/final failure | Validé |
| PostgreSQL WAL/PITR + daily full backup | Validé |
| Backup retention 14d fast + 30d standard | Validé |
| Deleted media may remain in encrypted backups until expiry | Validé |
| Encryption DB/storage/backups at rest | Validé |
| TLS everywhere | Validé |
| No secrets in Git | Validé |
| AI platform key secret manager/env | Validé |
| BYOK/per-establishment key post-MVP | Validé |
| Storage credentials backend-only | Validé |
| Rate limits critical endpoints | Validé |
| CORS allowlist, no wildcard prod | Validé |
| Bearer token auth requires protected token storage/CORS | Validé |
| No raw HTML UGC | Validé |
| Server-side file validation | Validé |
| Signed URL TTL 10 min + RBAC | Validé |
| Realtime authenticated/scoped channels | Validé |
| Push payload minimal | Validé |
| Incident process MVP | Validé |
| Processor breach notice to client/controller | Validé |
| No prod data in dev/staging | Validé |
| Prod DB access limited/logged | Validé |
| Admin/support console minimal | Validé |
| Synthetic data for dev/test/demo | Validé |
| MVP monitoring alerts | Validé |
| Manual export support MVP | Validé |
| Controlled offboarding/deletion procedure | Validé |
| Manual DSAR process with client/controller coordination | Validé |
| Subprocessors list maintained | Validé |
| PWA security baseline | Validé |
| Final principle validé | Validé |

---

# 30. Points à traiter ailleurs

## 30.1 Legal pack

À produire/valider juridiquement :
- DPA ;
- privacy policy ;
- subprocessors page ;
- client terms ;
- pilot agreement.

## 30.2 Technical Architecture / ERD

À intégrer :
- retention jobs ;
- policies ;
- auth tokens ;
- membership revocation ;
- audit/security logs ;
- admin/support access model.

## 30.3 API Contract

À intégrer :
- auth ;
- rate limit errors ;
- authorization failures ;
- signed URLs ;
- DSAR/export admin endpoints éventuels.

## 30.4 Ops / Monitoring

À cadrer :
- alerting ;
- backup restore process ;
- incident runbook ;
- support process ;
- provider outages.

---

# 31. Recommandation finale

La baseline Security / RGPD est suffisamment cadrée pour le MVP.

Décision centrale :

```txt
Privacy by design.
Least privilege.
Minimal data.
Controlled retention.
Secure by default.
```

Le build doit maintenant s’appuyer sur :
- backend authorization partout ;
- EstablishmentMembership comme scope d’accès ;
- logs minimisés ;
- aucune donnée brute sensible dans events/notifications/push/logs ;
- object storage privé ;
- signed URLs avec RBAC ;
- hébergement France/UE ;
- DPA avant pilote réel ;
- retention jobs ;
- backups chiffrés testés ;
- incident process minimal ;
- subprocessors list ;
- monitoring sécurité MVP.
# Checkpoint 1 auth security note

Current backend auth security baseline:

- access token = opaque bearer token, memory-only on the frontend
- refresh token = rotating opaque token in an HttpOnly cookie
- login, refresh, and logout are CSRF-protected mutation endpoints
- `SameSite=Lax` is defense in depth and does not replace CSRF validation
- raw tokens must not be stored or logged

Before production:

- add login rate limiting
- add refresh rate limiting
- add monitoring and alerting for suspicious refresh-token reuse
