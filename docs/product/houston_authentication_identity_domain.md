# Houston — Authentication / Identity Domain

**Version:** v0.1  
**Date:** 2026-05-24  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — identité utilisateur, authentification, invitations, activation, sessions, tokens, password reset, révocation

**Documents liés :**
- `Houston_rbac_permissions_domain.md`
- `Houston_security_rgpd_baseline.md`
- `Houston_notification_matrix.md`
- `Houston_event_catalog.md`
- `Houston_onboarding_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Authentication / Identity** de Houston.

Il définit :
- comment les utilisateurs s’authentifient ;
- les types d’identité supportés ;
- les règles pour Staff sans email professionnel ;
- le cycle d’invitation ;
- l’activation compte ;
- le login ;
- les sessions ;
- les tokens ;
- le refresh ;
- le logout ;
- la révocation ;
- le reset password ;
- les événements Auth ;
- les tables recommandées ;
- les tests fonctionnels MVP.

Ce document distingue clairement :

```txt
Authentication = qui est l’utilisateur ?
Authorization / RBAC = que peut-il faire ?
EstablishmentMembership = dans quel établissement agit-il, avec quel rôle/domaines ?
```

---

# 2. Principe central

```txt
Authentication proves identity.
Sessions are short-lived and revocable.
Refresh tokens rotate.
Backend remains authority for membership and permissions.
```

En français :

```txt
L’authentification prouve l’identité.
Les sessions sont courtes et révocables.
Les refresh tokens tournent.
Le backend reste l’autorité sur les memberships et permissions.
```

---

# 3. Décision structurante — deux identities d’authentification

## 3.1 Identities supportées

```txt
Houston supports two authentication identities:

1. Email identity
- required for Owner/Director/Manager

2. Username identity
- allowed for Staff
- managed by establishment managers
```

## 3.2 Shared accounts interdits

```txt
Shared accounts forbidden.
1 real user = 1 account.
```

## 3.3 Pourquoi

Certains utilisateurs Staff terrain n’ont pas d’email professionnel.

Imposer un email à tous les Staff créerait :
- friction onboarding ;
- faux emails ;
- comptes partagés ;
- adoption terrain faible ;
- support inutilement complexe.

Décision MVP :

```txt
Owner / Director / Manager
= email identity required

Staff
= email optional
= username identity allowed
```

---

# 4. Authentication vs Authorization

## 4.1 Authentication

```txt
Authentication = identifier l’utilisateur, gérer l’accès session, les credentials, les tokens et la révocation.
```

Authentication gère :
- identité ;
- credentials ;
- login ;
- activation ;
- sessions ;
- access tokens ;
- refresh tokens ;
- logout ;
- password reset ;
- révocation.

## 4.2 RBAC

```txt
RBAC = décider ce que l’utilisateur peut faire.
```

RBAC gère :
- rôle ;
- permissions ;
- operational_domains ;
- visibilité ;
- capacité d’action.

## 4.3 EstablishmentMembership

```txt
User s’authentifie globalement.
EstablishmentMembership détermine ensuite son accès établissement.
```

---

# 5. User global et établissement courant

## 5.1 User global

`User` est global.

Il peut avoir :
- 1 EstablishmentMembership ;
- plusieurs EstablishmentMemberships.

## 5.2 Après login

```txt
Après login :
- 1 membership actif → établissement sélectionné automatiquement
- plusieurs memberships actifs → establishment switcher
```

## 5.3 Current context

Chaque requête authentifiée doit résoudre :
- `current_user` ;
- `current_establishment` ;
- `current_membership`.

---

# 6. Méthodes d’authentification MVP

## 6.1 MVP

```txt
MVP authentication = email + password.
Magic link / SSO post-MVP.
```

## 6.2 Email identity

Utilisée pour :
- Owner ;
- Director ;
- Manager.

Règles :
- email obligatoire ;
- email verification required before account activation ;
- password required.

## 6.3 Username identity

Utilisée pour :
- Staff sans email professionnel.

Règles :
- email optionnel ;
- `login_identifier` obligatoire ;
- password required ;
- gérée par establishment managers.

---

# 7. Staff sans email professionnel

## 7.1 Décision

Staff peut s’authentifier via :

```txt
login_identifier + password
```

## 7.2 User fields

Staff username identity peut avoir :

```txt
email = null
login_identifier = present
identity_type = username
```

## 7.3 Login identifier

Ne pas utiliser un prénom seul.

Mauvais :

```txt
julien
marie
```

Recommandé :

```txt
mama_nice_hk_024
mn_staff_284
mama_bar_012
```

## 7.4 Pourquoi

Un identifiant Staff doit limiter :
- collisions ;
- énumération ;
- usurpation ;
- confusion support.

## 7.5 Reset Staff sans email

Staff username identity ne reçoit pas de reset password par email.

MVP recommandé :

```txt
Manager-assisted password reset.
```

Flow :
- Manager/Director réinitialise le mot de passe Staff ;
- système génère un mot de passe temporaire ;
- Staff doit changer ce mot de passe au prochain login ;
- action tracée en event/security log.

---

# 8. Invitation-first

## 8.1 Pas de public signup MVP

```txt
MVP = invitation-only.
No public self-signup.
```

## 8.2 Permissions d’invitation

```txt
Owner peut inviter Director/Manager/Staff
Director peut inviter Manager/Staff
Manager peut inviter Staff
Staff ne peut pas inviter
```

## 8.3 Invitation creates

```txt
Invitation creates:
- User pending if unknown
- EstablishmentMembership invited
- invitation token
```

## 8.4 Existing User

```txt
Existing User + new EstablishmentMembership invited.
```

## 8.5 Invitation includes intended access

```txt
Invitation includes intended role and operational_domains.
Backend validates inviter permission.
```

---

# 9. Invitation lifecycle

## 9.1 Invitation token

```txt
invitation_token_ttl = 7 days
single-use
revocable
```

## 9.2 Expired invitation

```txt
Expired invitation → new invitation token can be issued by authorized user.
```

## 9.3 Accept invitation

```txt
Accept invitation:
- verify token
- set password if needed
- set username
- activate User if pending
- activate Membership
- create session
```

## 9.4 Matching identity

```txt
Invitation acceptance requires matching email identity.
```

Interprétation :
- pour `email identity`, l’email doit correspondre à l’invitation ;
- pour `username identity`, le `login_identifier` est créé/attribué par l’établissement et doit correspondre à l’invitation Staff.

---

# 10. Statuses

## 10.1 User statuses

```txt
User statuses:
- pending
- active
- suspended
- deleted
```

## 10.2 EstablishmentMembership statuses

```txt
EstablishmentMembership statuses:
- invited
- active
- deactivated
```

## 10.3 Membership deactivation

```txt
Membership deactivation revokes access to that establishment immediately.
If no active memberships remain, user session becomes unusable.
```

## 10.4 User suspended

```txt
User suspended → revoke all sessions immediately.
```

---

# 11. Login flow

## 11.1 Email identity login

```txt
email + password
```

## 11.2 Username identity login

```txt
login_identifier + password
```

## 11.3 Generic identifier

Le backend peut exposer un champ générique :

```txt
identifier
password
```

`identifier` peut être :
- email ;
- login_identifier.

## 11.4 Login success

Si credentials valides :
- créer ou mettre à jour `UserSession` ;
- émettre access token ;
- établir refresh mechanism ;
- résoudre memberships actifs ;
- auto-select establishment si un seul ;
- demander selection si plusieurs.

## 11.5 Anti-enumeration

```txt
Login/reset responses must not reveal whether email exists.
```

À adapter pour username identity :

```txt
Login/reset responses must not reveal whether identifier exists.
```

---

# 12. Access token

## 12.1 Type

```txt
Access token short-lived.
Option recommandée : JWT très court-lived.
```

## 12.2 TTL

```txt
access_token_ttl = 15 minutes
```

## 12.3 Claims

```txt
Access token claims:
- sub/user_id
- session_id
- exp
- iat
- token_version/jti
No sensitive payload.
```

## 12.4 Interdiction

Ne pas mettre `operational_domains` comme claims autoritaires dans un JWT long.

```txt
Tokens must not be authority for permissions.
Authorization reads current EstablishmentMembership.
```

---

# 13. Refresh token

## 13.1 Required

```txt
Refresh token required for persistent sessions.
```

## 13.2 Type

```txt
Refresh token = opaque high-entropy random token.
Store only digest in DB.
```

## 13.3 Storage backend

```txt
Store refresh token digest/hash in DB.
Never store raw refresh token.
```

## 13.4 TTL

```txt
refresh_token_ttl = 30 days sliding
absolute_session_ttl = 90 days
```

## 13.5 Rotation

```txt
Refresh token rotation on every refresh.
Old refresh token immediately invalidated.
```

## 13.6 Reuse detection

```txt
Refresh token reuse detected → revoke token family + force re-login.
```

---

# 14. Token storage frontend

## 14.1 Preferred strategy

```txt
Preferred:
- access token in memory
- refresh token in secure httpOnly cookie if feasible
```

## 14.2 Alternative API/mobile-ready

```txt
Alternative API/mobile-ready:
- secure token storage strategy documented
- never store long-lived tokens casually in localStorage
```

## 14.3 PWA warning

Ne pas stocker durablement :
- refresh token accessible JS si évitable ;
- credentials ;
- raw operational content ;
- audio ;
- photos.

---

# 15. User sessions

## 15.1 UserSession par device/browser

```txt
Create UserSession per device/browser.
Track refresh token family, user_agent, last_used_at, revoked_at.
```

## 15.2 Metadata légère

```txt
Store light session metadata:
- user_agent
- ip truncated/last_ip optional
- created_at
- last_used_at
No invasive fingerprinting MVP.
```

## 15.3 Sessions expire

```txt
Sessions expire by refresh_token_ttl and absolute_session_ttl.
```

## 15.4 user_sessions table

```txt
user_sessions:
- id
- user_id
- status
- refresh_token_digest
- refresh_token_family_id
- user_agent
- ip_metadata
- last_used_at
- expires_at
- revoked_at
- created_at
```

---

# 16. Logout / revocation

## 16.1 Logout

```txt
Logout = revoke current refresh token/session server-side.
```

## 16.2 Logout all devices

```txt
Logout all devices = revoke all active sessions for User.
```

## 16.3 Revocation policy

```txt
Revoke sessions when:
- logout
- logout all devices
- password reset success
- user suspended
- membership deactivated if no active context
- refresh token reuse detected
- security incident
```

## 16.4 token_version

```txt
User.token_version or session token_version recommended.
Increment to invalidate existing access tokens if needed.
```

---

# 17. Password policy

## 17.1 Password rules

```txt
Password policy:
- min 8 chars
- password strength meter
- common/breached password blocklist if feasible
- no periodic forced rotation
- force reset only if compromise suspected
```

## 17.2 Password hashing

```txt
Use proven password hashing:
- Argon2id preferred if available
- bcrypt acceptable MVP
No homemade crypto.
```

---

# 18. Password reset

## 18.1 Required MVP

```txt
Password reset MVP required.
```

## 18.2 Token

```txt
password_reset_token_ttl = 30 minutes
single-use token
```

## 18.3 Reset success

```txt
Password reset success → revoke all existing sessions.
```

## 18.4 Security email

```txt
Password reset/changed → security email.
```

For Staff username identity without email :
- use manager-assisted reset ;
- no email delivery required ;
- event/security log required.

---

# 19. MFA / SSO / Passkeys

## 19.1 MFA

Decision:

```txt
No MFA MVP.
```

## 19.2 SSO / OAuth

```txt
SSO/OAuth post-MVP.
Design User identity model to allow external_identity later.
```

## 19.3 Passkeys / WebAuthn

```txt
Passkeys/WebAuthn post-MVP.
Keep authentication extensible.
```

---

# 20. Rate limiting / throttling

## 20.1 Login

```txt
Rate limit login by IP + email fingerprint.
```

À adapter pour username identity :

```txt
Rate limit login by IP + identifier fingerprint.
```

## 20.2 Password reset

```txt
Rate limit password reset by IP + email.
Generic response always.
```

À adapter pour username identity :

```txt
Rate limit password reset by IP + identifier.
Generic response always.
```

## 20.3 Refresh

```txt
Rate limit refresh endpoint per session/user/IP.
```

## 20.4 Lockout

```txt
Use progressive throttling / temporary delays.
Avoid hard account lockout MVP.
```

---

# 21. Email / username changes

## 21.1 Email verification

```txt
Email verification required before account activation.
```

For email identity only.

## 21.2 Email change

```txt
Email change post-MVP.
If MVP needed: new email verification + session review.
```

## 21.3 Username change

Staff username changes should be restricted.

Recommendation:

```txt
Only authorized Manager/Director/Admin can change Staff login_identifier.
Changing login_identifier must not change audit identity.
```

---

# 22. Authorization impact

## 22.1 Role/domain changes

```txt
Tokens must not be authority for permissions.
Authorization reads current EstablishmentMembership.
Role/domain change affects next request immediately.
```

## 22.2 JWT caution

Ne pas mettre les `operational_domains` comme claims autoritaires dans un JWT long.

Les claims peuvent être indicatifs, mais le backend doit vérifier la DB.

## 22.3 Membership status

Chaque requête doit vérifier :
- membership active ;
- establishment context ;
- role ;
- operational_domains si nécessaire.

---

# 23. Invitations model

## 23.1 invitations table

Version MVP adaptée aux deux identities :

```txt
invitations:
- id
- establishment_id
- email nullable
- login_identifier nullable
- identity_type
- role
- operational_domains
- invited_by_id
- token_digest
- status
- expires_at
- accepted_at
```

## 23.2 identity_type

```txt
identity_type:
- email
- username
```

## 23.3 Invitation email

For email identity:

```txt
Invitation email:
- establishment name
- inviter name optional
- activation link
- no sensitive operational data
```

## 23.4 Staff username identity invitation

For username identity:
- login_identifier generated or chosen by authorized manager ;
- temporary password generated ;
- Staff changes password at first login ;
- no sensitive operational data shown.

---

# 24. User model implications

## 24.1 users table

```txt
users:
- id
- email nullable
- login_identifier nullable
- identity_type
- password_digest
- status
- token_version
- email_verified_at nullable
- last_login_at nullable
- created_at
- updated_at
```

## 24.2 Constraints

```txt
If identity_type = email:
- email required
- email unique

If identity_type = username:
- login_identifier required
- login_identifier unique
- email optional
```

## 24.3 Recommendation

```txt
login_identifier globally unique with establishment prefix.
```

Example:

```txt
mama_nice_hk_024
```

---

# 25. Concrete authentication flows

## 25.1 Email identity flow

```txt
1. User receives invitation email
2. User opens activation link
3. User verifies email / sets password
4. User account becomes active
5. Membership becomes active
6. User logs in with email/password
7. Backend creates session
8. Frontend receives access token + refresh mechanism
9. If one active membership → selected automatically
10. If multiple active memberships → user selects establishment
11. Every API request checks current user + membership/RBAC
```

## 25.2 Username identity Staff flow

```txt
1. Manager creates/invites Staff
2. System creates User pending with username identity
3. System creates login_identifier
4. System creates Membership invited
5. Temporary password is generated
6. Staff logs in with login_identifier + temporary password
7. Staff sets/changess password if required
8. User becomes active if pending
9. Membership becomes active
10. Backend creates session
11. If one active membership → selected automatically
12. Every API request checks current user + membership/RBAC
```

## 25.3 Multiple memberships

```txt
If multiple active memberships:
- show establishment switcher
- selected establishment becomes current context
- all API requests are scoped to selected establishment
```

---

# 26. Auth events

## 26.1 Auth events

```txt
Auth events:
UserInvited
InvitationAccepted
UserActivated
LoginSucceeded
LoginFailed
LogoutSucceeded
RefreshTokenRotated
RefreshTokenReuseDetected
SessionRevoked
AllSessionsRevoked
PasswordResetRequested
PasswordResetSucceeded
PasswordChanged
EmailVerified
MembershipDeactivated
```

## 26.2 LoginFailed payload

```txt
LoginFailed event/security log with minimal payload:
- user_id if known
- email_hash
- identifier_hash for username identity
- ip metadata
- reason_code
No raw password.
```

## 26.3 New login notification

Decision:

```txt
No new-login notification MVP.
```

---

# 27. Security rules

## 27.1 No sensitive payload

Tokens and logs must not include :
- raw password ;
- refresh token raw ;
- operational_domains as authoritative claims ;
- sensitive operational content.

## 27.2 IP metadata

```txt
Store IP metadata minimally:
- recent IP for security if needed
- retention limited
- avoid long-term unnecessary IP storage
```

## 27.3 Account enumeration

```txt
Login/reset responses must not reveal whether identifier exists.
```

## 27.4 Password reset / change

```txt
Password reset/changed → security email.
```

Where email identity exists. For Staff username identity, use manager-assisted recovery.

---

# 28. Data model summary

## 28.1 users

```txt
users
├── id
├── email nullable
├── login_identifier nullable
├── identity_type
├── password_digest
├── status
├── token_version
├── email_verified_at nullable
├── last_login_at nullable
├── created_at
└── updated_at
```

## 28.2 user_sessions

```txt
user_sessions
├── id
├── user_id
├── status
├── refresh_token_digest
├── refresh_token_family_id
├── user_agent
├── ip_metadata
├── last_used_at
├── expires_at
├── revoked_at
├── created_at
└── updated_at
```

## 28.3 invitations

```txt
invitations
├── id
├── establishment_id
├── email nullable
├── login_identifier nullable
├── identity_type
├── role
├── operational_domains
├── invited_by_id
├── token_digest
├── status
├── expires_at
├── accepted_at
├── created_at
└── updated_at
```

---

# 29. Tests fonctionnels MVP

## 29.1 Email identity invitation

```txt
Given Owner invites Manager with email
When invitation is created
Then pending User is created if unknown
And Membership is invited
And invitation token is created
```

## 29.2 Username identity Staff invitation

```txt
Given Manager invites Staff without email
When invitation is created
Then User pending is created with identity_type=username
And login_identifier is generated
And Membership is invited
```

## 29.3 Shared account prevention

```txt
Given two real staff members
When manager tries to assign same account to both
Then product rules reject shared account usage
```

## 29.4 Login email

```txt
Given active email identity user
When user submits valid email/password
Then session is created
And access token is issued
And refresh token is rotated/stored as digest
```

## 29.5 Login username

```txt
Given active Staff username identity user
When user submits valid login_identifier/password
Then session is created
And establishment is auto-selected if one active membership
```

## 29.6 Membership deactivation

```txt
Given active session
When membership is deactivated
Then access to that establishment is revoked immediately
```

## 29.7 Refresh rotation

```txt
Given valid refresh token
When refresh endpoint is called
Then old refresh token is invalidated
And new refresh token is issued
```

## 29.8 Refresh reuse

```txt
Given old refresh token already rotated
When token is reused
Then refresh token family is revoked
And user must re-login
```

## 29.9 Password reset revokes sessions

```txt
Given user has active sessions
When password reset succeeds
Then all sessions are revoked
```

## 29.10 Role/domain change

```txt
Given user access token still valid
When membership role/domain changes
Then next API request uses current DB membership permissions
```

---

# 30. Décisions validées — index

| Décision | Statut |
|---|---:|
| Shared accounts forbidden | Validé |
| 1 real user = 1 account | Validé |
| Authentication = identity/session/credentials/tokens/revocation | Validé |
| RBAC = permissions | Validé |
| User global authenticates | Validé |
| Membership determines establishment access | Validé |
| 1 membership active = auto-select | Validé |
| Multiple memberships = switcher | Validé |
| MVP email + password | Validé |
| Magic link / SSO post-MVP | Validé |
| Email identity required for Owner/Director/Manager | Validé |
| Username identity allowed for Staff | Validé |
| Staff email optional | Validé |
| Username identity managed by establishment managers | Validé |
| Email verification required for account activation | Validé |
| Invitation-only MVP | Validé |
| No public self-signup | Validé |
| Owner can invite Director/Manager/Staff | Validé |
| Director can invite Manager/Staff | Validé |
| Manager can invite Staff | Validé |
| Staff cannot invite | Validé |
| Invitation creates User pending if unknown | Validé |
| Invitation creates Membership invited | Validé |
| Existing User + new Membership invited | Validé |
| User statuses pending/active/suspended/deleted | Validé |
| Membership statuses invited/active/deactivated | Validé |
| Membership deactivation revokes access immediately | Validé |
| JWT very short-lived recommended | Validé |
| Refresh token opaque hashed in DB | Validé |
| Access token TTL 15 min | Validé |
| Refresh token required | Validé |
| Refresh rotation every refresh | Validé |
| Refresh reuse revokes token family | Validé |
| Refresh TTL 30 days sliding | Validé |
| Absolute session TTL 90 days | Validé |
| No raw refresh token stored | Validé |
| Preferred access memory + refresh httpOnly cookie | Validé |
| UserSession per device/browser | Validé |
| Light metadata, no invasive fingerprinting | Validé |
| Logout revokes current session | Validé |
| Logout all devices available | Validé |
| Password reset MVP | Validé |
| Reset token TTL 30 min single-use | Validé |
| Reset revokes all sessions | Validé |
| Anti-account enumeration | Validé |
| Password min 8 chars | Validé |
| Strength meter/blocklist if feasible | Validé |
| No periodic forced rotation | Validé |
| Argon2id preferred / bcrypt acceptable | Validé |
| MFA not MVP | Validé |
| Invitation token TTL 7 days | Validé |
| Expired invitation can be reissued | Validé |
| Accept invitation activates User/Membership/session | Validé |
| Email identity acceptance requires matching email | Validé |
| Email change post-MVP | Validé |
| Rate limits login/reset/refresh | Validé |
| Progressive throttling, no hard lockout MVP | Validé |
| Auth events validated | Validé |
| LoginFailed minimal payload | Validé |
| No new-login notification MVP | Validé |
| Password reset/changed security email | Validé |
| User suspended revokes all sessions | Validé |
| Tokens not authority for permissions | Validé |
| Backend checks current EstablishmentMembership | Validé |
| Access token minimal claims | Validé |
| invitations table adapted to email/username identities | Validé |
| Invitation includes role/domains | Validé |
| Invitation email minimal | Validé |
| Revocation policy validated | Validé |
| token_version recommended | Validé |
| IP metadata minimized | Validé |
| SSO/OAuth post-MVP | Validé |
| Passkeys/WebAuthn post-MVP | Validé |
| Final principle validated | Validé |

---

# 31. Points à traiter ailleurs

## 31.1 API Contract

À cadrer :
- login endpoint ;
- refresh endpoint ;
- logout ;
- logout all ;
- accept invitation ;
- password reset ;
- current session ;
- establishment switch.

## 31.2 Frontend / PWA

À cadrer :
- storage exact des tokens ;
- refresh flow ;
- session expiration UX ;
- Staff login screen ;
- establishment switcher.

## 31.3 Security / RGPD

Déjà cadré :
- logs ;
- token security ;
- rate limiting ;
- no prod data in dev ;
- no secrets in Git.

## 31.4 Admin / Support

À cadrer :
- manager-assisted Staff password reset ;
- session revocation UI ;
- user suspension ;
- invitation resend/revoke.

---

# 32. Recommandation finale

Le domaine Authentication / Identity est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Houston supports two authentication identities:
- Email identity for Owner/Director/Manager
- Username identity for Staff
```

Le build doit maintenant s’appuyer sur :
- `User` global ;
- `EstablishmentMembership` pour accès établissement ;
- invitation-only ;
- email/password pour Owner/Director/Manager ;
- username/password pour Staff sans email ;
- refresh token opaque hashé ;
- rotation refresh token ;
- sessions révocables ;
- backend authorization à chaque requête ;
- shared accounts interdits.
