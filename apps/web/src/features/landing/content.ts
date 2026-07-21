export const APP_LOGIN_URL = 'https://app.spore-os.com/login' as const

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

export const pricingContent = {
  title: 'Un prix qui suit votre développement',
  subtitle: "Signaux, plans d'action, suivi terrain — tout est inclus, dès le premier jour.",
  badge: 'OFFRE UNIQUE',
  price: '129€',
  priceSuffix: '/ mois / site',
  features: [
    'Toute la plateforme incluse',
    "Jusqu'à 5 pôles d'activité",
    'Utilisateurs illimités',
  ] as const,
  trialCta: "Démarrer l'essai gratuit — 14 jours",
  comingSoonLabel: 'Bientôt disponible',
  poleExtension: {
    title: 'Votre établissement a plus de 5 pôles d’activité ?',
    body: 'Food hall, resort, tiers-lieux — +15€/mois par pôle supplémentaire. Aucune surprise, aucune négociation : le même principe s’applique à tout le monde.',
  },
  multiSite: {
    title: 'Vous gérez plusieurs établissements ?',
    body: 'Ajoutez le pilotage groupe : reporting consolidé, benchmark inter-sites, un seul tableau de bord. À partir de 149€/mois, quel que soit le nombre de sites dans la tranche.',
    detailCta: 'Voir le détail',
  },
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
  copyright: '© 2026 Spore. Tous droits réservés.',
} as const

export const soonAvailableMessages = {
  demo: 'Les demandes de démo seront bientôt disponibles.',
  trial: "L'essai gratuit sera bientôt disponible.",
  group: 'Le pilotage groupe sera bientôt disponible.',
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
