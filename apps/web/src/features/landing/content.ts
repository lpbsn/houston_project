export const APP_LOGIN_URL = 'https://app.spore-os.com/login' as const
export const APP_PROFILE_URL = 'https://app.spore-os.com/general' as const
export const ACCOUNT_DELETION_SUPPORT_EMAIL = 'leonard.p.boisson@gmail.com' as const

export const landingSeo = {
  home: {
    title: 'Spore — L’OS des équipes terrain',
    description:
      'Spore transforme les observations terrain en actions structurées et suivies, pour améliorer l’efficacité opérationnelle et donner une visibilité totale aux directions.',
    canonical: 'https://spore-os.com/',
  },
  legal: {
    title: 'Mentions légales — Spore',
    description:
      'Mentions légales du site Spore : éditeur, responsable de publication, hébergeur et informations de conformité.',
    canonical: 'https://spore-os.com/mentions-legales/',
  },
  accountDeletion: {
    title: 'Supprimer un compte Spore',
    description:
      'Comment demander la suppression de votre compte Spore et des données personnelles associées.',
    canonical: 'https://spore-os.com/supprimer-compte/',
  },
  support: {
    title: 'Support — Spore',
    description: 'Contacter le support Spore pour une question sur le compte ou l’application.',
    canonical: 'https://spore-os.com/support/',
  },
} as const

export const heroContent = {
  h1: 'Transforme chaque observation terrain en action résolue.',
  h1Accent: 'résolue',
  lead: "Des centaines d'opportunités d'augmenter les revenus de votre établissement passent tous les jours sous vos radars.",
  support: "Avec Spore, activez 100% de ces leviers d'amélioration en quelques secondes.",
  cta: 'Demander une démo',
  sectorsLabel: 'CONÇU POUR LES EXPLOITANTS',
  sectors: ['Hôtel', 'Restaurant', 'Loisirs', 'Bureaux', 'Retail'] as const,
} as const

export type FloatingObservation = {
  id: string
  label: string
  tone: 'neon' | 'moss' | 'soft' | 'white'
  /** Desktop position as % of the swarm container (md+) */
  x: number
  y: number
  /** Optional lg+ overrides to avoid collisions with the wider card */
  xLg?: number
  yLg?: number
  /** Optional xl+ overrides */
  xXl?: number
  yXl?: number
  delay: number
  mobile?: boolean
}

export const floatingObservations: FloatingObservation[] = [
  { id: 'o1', label: 'Climatisation HS salle B', tone: 'neon', x: 8, y: 12, delay: 0, mobile: true },
  { id: 'o2', label: 'Enfant perdu -> retrouvé ✅', tone: 'soft', x: 72, y: 8, xLg: 78, delay: 0.4, mobile: true },
  { id: 'o3', label: 'La caisse 2 bloque', tone: 'neon', x: 78, y: 28, xLg: 84, delay: 0.8, mobile: true },
  { id: 'o4', label: "Besoin d'aide en cuisine !", tone: 'moss', x: 4, y: 38, delay: 1.1, mobile: true },
  { id: 'o5', label: 'Livraison arrivée 👍', tone: 'soft', x: 82, y: 48, xLg: 86, delay: 0.2 },
  { id: 'o6', label: 'La porte ne ferme plus', tone: 'white', x: 12, y: 58, xLg: 4, yLg: 64, delay: 1.5 },
  {
    id: 'o7',
    label: 'Machine à café en panne ☕',
    tone: 'white',
    x: 70,
    y: 62,
    xLg: 78,
    yLg: 70,
    delay: 0.6,
  },
  { id: 'o8', label: 'Table 8 attend depuis 20min', tone: 'moss', x: 18, y: 78, xLg: 10, yLg: 84, delay: 1.0, mobile: true },
  { id: 'o9', label: 'Bruit anormal cuisine', tone: 'soft', x: 58, y: 18, xLg: 68, yLg: 10, delay: 1.3 },
  { id: 'o10', label: 'Stock serviettes bas', tone: 'white', x: 48, y: 5, delay: 0.9 },
  { id: 'o11', label: 'Client VIP arrive', tone: 'neon', x: 88, y: 72, delay: 0.5, mobile: true },
  { id: 'o12', label: 'Fuite sanitaires R+1', tone: 'moss', x: 2, y: 22, delay: 1.6 },
  { id: 'o13', label: 'Wi-Fi salon HS', tone: 'white', x: 55, y: 80, xLg: 62, yLg: 88, delay: 0.3, mobile: true },
  { id: 'o14', label: 'Lit cassé chambre 214', tone: 'soft', x: 30, y: 8, xLg: 22, yLg: 4, delay: 1.2 },
]

export const problemContent = {
  badge: 'LE PROBLÈME',
  title: "Chaque jour, vos équipes remontent des dizaines d'observations :",
  items: ['des problèmes,', 'des idées,', 'des anomalies,', 'des demandes clients.'] as const,
  body:
    'Au fil de la journée, toutes ces informations se retrouvent noyées dans des centaines de messages, répartis sur plusieurs conversations et plusieurs canaux.',
  consequencesLabel: 'LES CONSÉQUENCES',
  consequences: [
    'Des observations importantes passent inaperçues.',
    'Les bonnes personnes ne voient pas toujours les bonnes informations.',
    "Personne ne sait si une observation a réellement été traitée.",
    'Les mêmes problèmes reviennent encore et encore.',
  ] as const,
  closing: "Des opportunités d'amélioration perdues.",
} as const

export const transitionContent = {
  lineBefore: 'Des outils pour',
  mutedWord: 'parler',
  lineAfter: 'Aucun pour',
  accentWord: 'agir',
} as const

export const solutionContent = {
  badge: 'La solution',
  tagline: 'Le premier OS pour les équipes terrain.',
} as const

export const howItWorksContent = {
  title: "De l'observation au ticket résolu, en trois étapes.",
  steps: [
    {
      number: '01',
      title: 'Capturer en 5 secondes',
      body: 'Un collaborateur envoie une observation par écrit ou vocal. Notre IA la transforme en message structuré et catégorisé.',
      icon: 'mic' as const,
    },
    {
      number: '02',
      title: 'Transformer en action',
      body: "Les concernés sont notifiés, et en quelques secondes peuvent créer un plan d'action avec un responsable, une deadline...",
      icon: 'sparkles' as const,
    },
    {
      number: '03',
      title: 'Suivre la résolution',
      body: "En un coup d'œil vous suivez dans le détail la résolution des plans d'actions.",
      icon: 'clipboard' as const,
    },
  ] as const,
  metrics: [
    { value: '5s', label: 'pour capturer une observation' },
    { value: '100%', label: 'des observations traitées' },
  ] as const,
} as const

export const directionContent = {
  badge: 'POUR LA DIRECTION',
  titleBefore: 'Du temps gagné. Une',
  titleAccent: 'visibilité totale.',
  body: 'Les observations terrain sont le meilleur indicateur de la qualité réelle de vos établissements. Spore les centralise pour que vous puissiez piloter en quelques minutes.',
  cards: [
    {
      number: '01',
      title: 'Visibilité',
      body: "En quelques minutes, voyez tout ce qui se passe dans l'établissement.",
    },
    {
      number: '02',
      title: 'Décision',
      body: 'Problèmes récurrents, délais de résolution... Enfin de la data concrètes.',
    },
    {
      number: '03',
      title: 'Performance',
      body: 'Chaque observation devient une action.',
    },
  ] as const,
} as const

export const finalCtaContent = {
  title: "Prêt à exploiter l'intelligence de votre terrain ?",
  cta: 'Demander une démo',
} as const

export const footerContent = {
  loginLabel: 'Se connecter',
  loginHref: APP_LOGIN_URL,
  legalLabel: 'Mentions légales',
  legalHref: '/mentions-legales/',
  privacyLabel: 'Confidentialité',
  privacyHref: '/politique-de-confidentialite/',
  termsLabel: 'Conditions d’utilisation',
  termsHref: '/conditions-d-utilisation/',
  accountDeletionLabel: 'Supprimer un compte',
  accountDeletionHref: '/supprimer-compte/',
  supportLabel: 'Support',
  supportHref: '/support/',
  copyright: '© 2026 Spore. Tous droits réservés.',
} as const

export const soonAvailableMessages = {
  demo: 'Les demandes de démo seront bientôt disponibles.',
} as const

export const legalContent = {
  pageTitle: 'Mentions légales',
  backLabel: 'Retour à l’accueil',
  backHref: '/',
  sections: [
    {
      title: 'Éditeur',
      paragraphs: [
        'Léonard Boisson, personne physique opérant sous la marque Spore / Spore OS.',
        'Adresse : 108 rue de la Tour, 75116 Paris, France.',
        'Téléphone : +33 6 46 77 12 55',
        'Email : leonard.p.boisson@gmail.com',
      ],
    },
    {
      title: 'Responsable de publication',
      paragraphs: ['Léonard Boisson'],
    },
    {
      title: 'Hébergeur',
      paragraphs: [
        'Railway Corporation',
        '548 Market St Suite 68956, San Francisco, California 94104, États-Unis',
        'Téléphone : +1 415 707 7675',
        'Email : team@railway.com',
        'Région d’exécution actuelle des services : EU West — Amsterdam, Pays-Bas. Cette région technique ne remplace pas l’identité légale de l’hébergeur.',
      ],
    },
    {
      title: 'Données personnelles et cookies',
      paragraphs: [
        'La landing publique MVP ne collecte aucune donnée personnelle.',
        'Aucun outil d’analytics et aucun cookie non essentiel ne sont utilisés sur cette surface.',
        'La politique de confidentialité de l’application Spore est publiée à l’adresse https://spore-os.com/politique-de-confidentialite/.',
      ],
    },
    {
      title: 'Propriété intellectuelle',
      paragraphs: [
        'Le contenu, l’identité visuelle et le logo Spore sont protégés. Toute reproduction non autorisée est interdite.',
      ],
    },
  ] as const,
} as const

export const accountDeletionContent = {
  pageTitle: 'Supprimer un compte Spore',
  backLabel: 'Retour à l’accueil',
  backHref: '/',
  intro:
    'Si vous avez un compte Spore, vous pouvez demander la suppression de ce compte et des données personnelles associées.',
  inAppTitle: 'Depuis l’application',
  inAppParagraphs: [
    'Connectez-vous à Spore, ouvrez Profil, puis choisissez « Supprimer mon compte ».',
    'Confirmez avec votre mot de passe. Si vous êtes le seul propriétaire d’une organisation, la suppression ferme aussi cette organisation.',
  ] as const,
  loginLabel: 'Ouvrir Spore',
  loginHref: APP_PROFILE_URL,
  emailTitle: 'Si vous ne pouvez plus vous connecter',
  emailIntro:
    'Écrivez-nous. Indiquez l’adresse e-mail du compte. Nous traitons la demande sous 30 jours.',
  emailLabel: ACCOUNT_DELETION_SUPPORT_EMAIL,
  emailHref: `mailto:${ACCOUNT_DELETION_SUPPORT_EMAIL}?subject=Suppression%20de%20compte%20Spore`,
  retainedTitle: 'Ce qui est retiré et ce qui peut rester',
  retainedParagraphs: [
    'Nous retirons l’identifiant du compte (e-mail, nom, mot de passe, sessions, notifications push) et le contenu que vous avez soumis (texte d’observation, photos, commentaires, messages de chat encore présents).',
    'Le travail d’établissement déjà structuré (signaux, plans d’action) peut être conservé. Votre nom n’y est plus affiché. Des extraits peuvent encore apparaître dans des synthèses ou dans les textes écrits par d’autres personnes.',
  ] as const,
} as const

export const supportContent = {
  pageTitle: 'Support',
  backLabel: 'Retour à l’accueil',
  backHref: '/',
  intro:
    'Cette page est le contact support de Spore, pour les utilisateurs de l’application et pour les stores.',
  sections: [
    {
      title: 'Nous écrire',
      paragraphs: [
        `Email : ${ACCOUNT_DELETION_SUPPORT_EMAIL}`,
        'Indiquez l’adresse e-mail du compte concerné et le sujet (connexion, suppression, question sur l’application).',
        'Objectif de réponse : 30 jours. Les demandes urgentes de sécurité (compte compromis) sont traitées en priorité.',
      ],
    },
    {
      title: 'Compte et données',
      paragraphs: [
        'Suppression de compte : depuis Profil dans l’application, ou via https://spore-os.com/supprimer-compte/.',
        'Politique de confidentialité : https://spore-os.com/politique-de-confidentialite/.',
        'Conditions d’utilisation : https://spore-os.com/conditions-d-utilisation/.',
      ],
    },
    {
      title: 'Application',
      paragraphs: [
        'Spore est un outil d’exploitation pour des établissements identifiés. L’accès opérationnel nécessite un compte et une appartenance à un établissement actif.',
        'Connexion : https://app.spore-os.com/login',
      ],
    },
  ],
} as const

export const privacyPolicyContent = {
  pageTitle: 'Politique de confidentialité',
  backLabel: 'Retour à l’accueil',
  backHref: '/',
  intro:
    'Cette politique décrit les traitements réellement mis en œuvre par Spore au 2 septembre 2026, d’après le code du produit et l’inventaire des données. Elle n’est pas un avis juridique.',
  sections: [
    {
      title: 'Éditeur et contact',
      paragraphs: [
        'Spore est édité par Léonard Boisson, 108 rue de la Tour, 75116 Paris, France, leonard.p.boisson@gmail.com.',
        'Pour exercer vos droits (accès, rectification, suppression, opposition), utilisez la suppression de compte dans Profil ou écrivez à cette adresse. Objectif de traitement des demandes par e-mail : 30 jours.',
      ],
    },
    {
      title: 'Rôles',
      paragraphs: [
        'L’établissement client est responsable de traitement des dossiers opérationnels (observations, signaux, plans d’action, commentaires, chat d’équipe).',
        'FloorPower / Spore est sous-traitant de ce traitement opérationnel, et responsable de traitement des données de compte, de session et de sécurité de la plateforme.',
      ],
    },
    {
      title: 'Données collectées',
      paragraphs: [
        'Compte : e-mail ou identifiant, mot de passe haché, prénom, nom, identifiant interne, rôle et statut d’appartenance à un établissement.',
        'Session : jetons d’accès et de rafraîchissement sous forme de condensats, agent utilisateur, adresse IP (métadonnées de session), établissement sélectionné. Sur le web, le rafraîchissement utilise un cookie HttpOnly et un jeton CSRF. Sur Native, le rafraîchissement est stocké dans le stockage sécurisé Capacitor. Le jeton d’accès reste en mémoire.',
        'Contenu opérationnel : texte d’observation, photos privées, commentaires et mentions, messages de chat, signaux, plans d’action, notifications in-app, éventuel historique de gamification.',
        'Appareil : microphone pour la transcription (audio traité le temps de la requête, puis supprimé ; seul le texte est conservé). Photos via le sélecteur de fichiers. Jeton de notification push (FCM) si vous activez les notifications Native.',
        'Spore ne collecte pas de géolocalisation, carnet de contacts, biométrie, identifiant publicitaire, ni d’analytics produit via un SDK dédié.',
      ],
    },
    {
      title: 'Finalités',
      paragraphs: [
        'Fournir le compte, authentifier, isoler les établissements et appliquer les droits d’accès.',
        'Transformer une observation en signal et suivre les plans d’action.',
        'Permettre le chat d’équipe, les commentaires et les notifications.',
        'Assurer la sécurité des sessions et la suppression de compte.',
      ],
    },
    {
      title: 'Intelligence artificielle (OpenAI)',
      paragraphs: [
        'Le texte d’une observation peut être envoyé à OpenAI pour le pipeline de structuration en signal. L’audio de transcription est envoyé à OpenAI le temps de la requête, puis le fichier temporaire est détruit. Les photos et le chat ne sont pas envoyés à OpenAI.',
        'Un consentement versionné (openai-v1) est enregistré avant ces traitements, y compris le classement analytics qui envoie à OpenAI le titre, la synthèse structurée et le focus déjà produits sur le signal (pas le texte brut d’observation ni l’audio). Vous pouvez le retirer depuis Profil ; la transcription, l’analyse d’observation et ce classement deviennent alors indisponibles jusqu’à un nouveau consentement.',
        'Spore conserve des métadonnées d’usage IA (identifiants, modèle, statut), pas le prompt ni la sortie brute. La conservation chez OpenAI n’est pas contrôlée dans ce dépôt.',
      ],
    },
    {
      title: 'Sous-traitants et hébergement',
      paragraphs: [
        'Hébergement applicatif : Railway Corporation (entité légale aux États-Unis). Région d’exécution actuellement indiquée : EU West — Amsterdam. Cette région technique ne remplace pas l’identité légale de l’hébergeur.',
        'Base PostgreSQL et Redis sur cette infrastructure. E-mails d’invitation : Resend, lorsqu’une clé est configurée.',
        'Notifications Native : Firebase Cloud Messaging et, sur iOS, Apple Push Notification service. Le binaire Native lie Firebase Messaging (pas Firebase Analytics dans le projet actuel).',
        'Aucun Sentry, aucun outil marketing, aucun Web Push navigateur.',
      ],
    },
    {
      title: 'Durées',
      paragraphs: [
        'Messages de chat : suppression automatique des lignes de message après 7 jours.',
        'Fichiers temporaires orphelins : 24 heures. Audio de transcription : fin de requête.',
        'Médias d’observation : retirés lorsque le dernier signal actif créé à partir de l’observation disparaît.',
        'La conservation des journaux d’infrastructure Railway n’est pas spécifiée dans le dépôt.',
      ],
    },
    {
      title: 'Suppression de compte',
      paragraphs: [
        'Depuis Profil dans l’application, ou via https://spore-os.com/supprimer-compte/.',
        'Nous retirons e-mail, nom, mot de passe utilisable, sessions, jetons push, textes d’observation et photos soumis, corps des commentaires, messages de chat encore présents que vous avez écrits.',
        'Les dossiers d’établissement (signaux, plans d’action) peuvent rester, sans votre nom affiché. Des détails personnels peuvent subsister dans les textes d’autres personnes ou dans des synthèses déjà produites.',
      ],
    },
    {
      title: 'Transferts',
      paragraphs: [
        'OpenAI, Firebase et l’entité légale Railway peuvent impliquer un traitement hors de l’Espace économique européen. Les garanties contractuelles précises de ces fournisseurs ne sont pas dans ce dépôt ; elles doivent être lues dans leurs documentations et contrats en vigueur au moment du remplissage des stores.',
      ],
    },
    {
      title: 'Mineurs',
      paragraphs: [
        'Spore est un outil professionnel d’exploitation. Il n’est pas destiné aux enfants.',
      ],
    },
  ],
} as const

export const termsOfUseContent = {
  pageTitle: 'Conditions d’utilisation',
  backLabel: 'Retour à l’accueil',
  backHref: '/',
  intro:
    'Version cgu-v1. Ces conditions s’appliquent à l’usage de Spore. L’acceptation est enregistrée avant la publication de contenu visible par d’autres membres (observation, commentaire, message de chat). La transcription audio n’est pas un contenu publié et n’est pas conditionnée à ces conditions.',
  sections: [
    {
      title: 'Service',
      paragraphs: [
        'Spore est une application de terrain : observations, signaux, plans d’action, commentaires et chat d’équipe, pour des établissements identifiés.',
        'Le service est fourni par Léonard Boisson, opérant sous la marque Spore / Spore OS.',
      ],
    },
    {
      title: 'Compte et établissements',
      paragraphs: [
        'Vous devez fournir des informations exactes et garder vos identifiants confidentiels.',
        'L’accès opérationnel dépend de votre appartenance à un établissement et de votre rôle. L’éditeur peut suspendre un compte en cas d’usage abusif.',
      ],
    },
    {
      title: 'Contenu publié',
      paragraphs: [
        'Vous restez responsable des textes, photos et messages que vous publiez. N’y placez pas de données illicites, de contenus portant atteinte à autrui, ni de secrets que votre établissement n’autorise pas à traiter dans Spore.',
        'Les autres membres de l’établissement peuvent voir le contenu opérationnel selon les règles d’accès du produit.',
      ],
    },
    {
      title: 'Signalement et blocage',
      paragraphs: [
        'Vous pouvez signaler un contenu ou un membre. Le signalement est enregistré et l’opérateur est prévenu avec des identifiants, sans le corps du contenu dans l’e-mail.',
        'Vous pouvez bloquer un autre membre du même établissement. Cela empêche les nouveaux messages privés et les nouvelles mentions entre vous. L’historique déjà échangé reste lisible. Le travail opérationnel (fil, signaux, plans, commentaires sans nouvelle mention, chat de groupe) reste visible.',
        'Masquer une conversation privée n’est pas un blocage.',
      ],
    },
    {
      title: 'IA',
      paragraphs: [
        'L’analyse d’observation et la transcription utilisent OpenAI selon la politique de confidentialité et un consentement distinct, retirable dans Profil.',
      ],
    },
    {
      title: 'Disponibilité',
      paragraphs: [
        'Le service est fourni en l’état, sans garantie d’absence d’interruption. Les données opérationnelles appartiennent au contexte de l’établissement.',
      ],
    },
    {
      title: 'Droit applicable',
      paragraphs: [
        'Droit français. En cas de litige, les tribunaux français sont compétents, sous réserve des règles impératives de protection des consommateurs le cas échéant.',
      ],
    },
  ],
} as const

