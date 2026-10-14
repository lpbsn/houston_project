# Formulaire de contact de la landing — activation par Léo

Les quatre CTA commerciaux pointent vers `#sp-contact`. Le visiteur remplit nom,
e-mail, établissement/groupe, téléphone facultatif et message. L'envoi passe par
`POST /api/contact`, une **Cloudflare Pages Function** de la landing. Aucune modification
Django, migration, connexion au compte Spore ou modification Railway n'est nécessaire.

## Paramètres Cloudflare Pages

Root directory **`apps/web`**, build `npm ci && npm run build:landing`, sortie
`dist-landing`. Le dossier `apps/web/functions` est détecté par Pages à côté du projet,
pas dans `dist-landing`. Si le projet actuel a la racine Git comme Root directory,
passer à `apps/web` et adapter les deux chemins ci-dessus avant le déploiement.

Configurer séparément **Preview** et **Production** :

| Paramètre | Où | Valeur |
| --- | --- | --- |
| `VITE_TURNSTILE_SITE_KEY` | Variable de build publique | Clé du widget Turnstile |
| `TURNSTILE_SECRET_KEY` | Secret de la Function | Secret du même widget |
| `RESEND_API_KEY` | Secret de la Function | Clé Resend autorisée à envoyer |
| `CONTACT_FROM_EMAIL` | Variable serveur | Expéditeur sur un domaine vérifié dans Resend |
| `CONTACT_TO_EMAIL` | Variable serveur | Adresse de réception validée par Maxime, indiquée dans la PR |

**Ne jamais préfixer les paramètres serveur par `VITE_`.** Aucun destinataire n'est
inclus dans le JavaScript public ni dans la réponse de l'endpoint. Le bouton Répondre
dans l'e-mail utilise l'adresse du prospect, grâce au champ `reply_to`.

Créer le widget Turnstile pour les domaines effectivement utilisés (`spore-os.com`,
`www.spore-os.com` si utilisé, et l'hôte exact de la preview de branche). L'action
attendue est `contact`. Utiliser une adresse de réception de test pour Preview.
Ne pas utiliser les clés de démonstration Turnstile en production.

Sans configuration complète : le formulaire n'affiche aucun faux succès et ne peut
pas envoyer. Après modification de la clé publique, **reconstruire et redéployer**.
Un simple `vite preview` sert les fichiers statiques, pas la Function.

## Validation et activation

```bash
cd apps/web
npm run test -- --maxWorkers=1 src/features/landing
npm run test:landing-contact
npm run typecheck
npm run typecheck:landing-contact
npm run build:landing
npm exec --yes --package=wrangler@4.151.0 -- wrangler pages functions build functions --outdir /tmp/spore-contact-worker
```

Après configuration Preview, vérifier une demande de bout en bout avec une adresse
de test, sa réception dans la boîte, le reply-to, les erreurs et le réessai, puis
l'affichage sur mobile/ordinateur. Les tests automatisés simulent les fournisseurs :
ils n'envoient aucun e-mail réel. Le succès signifie que Resend a accepté l'envoi,
pas une garantie de livraison en boîte de réception. Surveiller les échecs/bounces
et le quota dans Resend après activation.

## Mentions à ajuster avant publication

Le fichier de contenu partagé contient encore « La landing publique MVP ne collecte
aucune donnée personnelle ». Le correctif minimal est fourni dans
`docs/deploy/landing-contact-privacy.patch` :

```bash
# Depuis la racine du dépôt, à appliquer par Léo avant activation :
git apply --check docs/deploy/landing-contact-privacy.patch
git apply docs/deploy/landing-contact-privacy.patch
```

Ce patch ne contient aucune coordonnée privée. La réécriture complète du fichier
partagé, qui contient aussi des coordonnées, avait été bloquée par le contrôle
automatique d'approbation ; elle n'a pas été contournée. Relire la notice avec les
modalités de conservation réelles des demandes et les contrats des prestataires.

## Garanties et limites techniques

- Origine identique obligatoire, méthode POST et JSON, corps limité à 32 Ko en lecture.
- Validation serveur des champs, piège anti-robot et vérification Turnstile côté serveur
  (jeton, hostname et action). Pas d'accès aux données métier ni aux sessions Spore.
- Destinataire imposé par le serveur ; pas de relais e-mail vers une adresse choisie
  par le client. Message en texte brut, aucun HTML utilisateur interprété.
- Délais réseau bornés. Erreurs sans contenu client, clé ou réponse fournisseur.
- Saisie conservée lors d'un échec ; double soumission bloquée pendant l'envoi.
- Clé d'idempotence Resend stable lors d'un réessai du même message ; un contenu
  modifié est une nouvelle demande. Nouvelle vérification anti-robot après tentative.
- Aucun abonnement marketing automatique ni accusé automatique envoyé au prospect.

Références :
- https://developers.cloudflare.com/pages/functions/get-started/
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- https://resend.com/docs/api-reference/emails/send-email
