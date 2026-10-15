# Présentation SaaS web et application terrain native

La surface produit dépend de `VITE_APP_RUNTIME`, pas de la largeur de fenêtre :

- `web` : SaaS, navigation latérale et pages web, même dans une fenêtre étroite ou
  dans le navigateur d'un téléphone.
- `native` : expérience terrain embarquée par Capacitor, même sur une tablette large.

`isDesktopWebLanding()` reste le point de décision partagé par le routage, la coque
et les pages. Il ne prend plus de largeur en paramètre. Son nom historique désigne
l'expérience SaaS et non la détection matérielle d'un ordinateur.

`useLgViewport()` et `useXlViewport()` restent des outils de disposition :
- rail latéral replié par défaut sous 1024 px, avec choix d'ouverture indépendant
  entre fenêtre compacte et large ;
- colonnes de formulaire selon l'espace disponible ;
- calendrier compact selon la place disponible ;
- chat web empilé sous 1024 px, toujours dans son espace SaaS, au lieu de deux
  colonnes qui écraseraient la conversation.

Spore Brain reste monté lorsque la fenêtre est réduite. Le bandeau d'indisponibilité
est réservé au runtime natif. Les contrôles de rôle et d'accès restent inchangés.
Le contexte de navigation du bas indique maintenant sa présence effective : aucune
barre terrain dans le web, et donc aucune réservation d'espace pour celle-ci.

## Revue avant fusion

1. Web : ouvrir Brain et réduire/agrandir la fenêtre sans perdre l'analyse affichée.
2. À 1440, 1024, 800 et 390 px : navigation, observation en cours de saisie, plan,
   calendrier, dashboard, menus, dialogues et chat ; vérifier absence de commandes
   coupées et possibilité de parcourir les tableaux larges.
3. Navigateur de téléphone : même SaaS, disposition compacte.
4. Native téléphone et tablette : navigation terrain, clavier, marges de sécurité,
   création d'observations et d'actions inchangées.
5. Comptes staff, manager et siège : vérifier que le redimensionnement ne modifie
   ni le contexte d'établissement ni les fonctions autorisées.

Aucun changement API, base de données ou configuration Capacitor. Aucun script de
migration. La PR vise staging et ne doit pas être déployée avant revue de Léo.
