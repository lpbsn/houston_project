import { useEffect } from 'react'
import {
  ArrowRight,
  Binoculars,
  ClipboardList,
  MessagesSquare,
  ShieldCheck,
  Waypoints,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { LandingCard } from '@/features/landing/components/landing-card'
import { LandingHero } from '@/features/landing/components/landing-hero'
import { LandingNavbar } from '@/features/landing/components/landing-navbar'
import { LandingPathLink } from '@/features/landing/components/landing-path-link'
import { LandingSection } from '@/features/landing/components/landing-section'

const CONSTAT_CARDS = [
  {
    eyebrow: 'Constat',
    title: 'Le terrain remonte des faits utiles, mais le suivi reste souvent diffus.',
    description:
      'Messages dispersés, arbitrages informels, relances inégales. Une partie de la valeur opérationnelle se perd avant même qu’une action claire soit décidée.',
    icon: <MessagesSquare className="size-5" />,
  },
  {
    eyebrow: 'Conséquence',
    title: 'Les managers passent du temps à reconstituer le contexte au lieu de piloter.',
    description:
      'Quand l’information reste brute, personne ne partage exactement la même lecture de la situation ni la même priorité.',
    icon: <Binoculars className="size-5" />,
  },
]

const LOOP_CARDS = [
  {
    eyebrow: '1. Observer',
    title: 'Capturer ce qui se passe vraiment sur le terrain.',
    description:
      'Houston part du réel: une observation courte, concrète, et exploitable pour démarrer une boucle opérationnelle propre.',
    icon: <Binoculars className="size-5" />,
  },
  {
    eyebrow: '2. Structurer',
    title: 'Transformer l’information brute en signal compréhensible.',
    description:
      'Le produit vise à rendre la situation lisible, cadrée et partageable, sans déplacer l’autorité métier hors du backend.',
    icon: <Waypoints className="size-5" />,
  },
  {
    eyebrow: '3. Agir',
    title: 'Coordonner des actions suivies jusqu’à la validation.',
    description:
      'Managers et équipes avancent sur une même image opérationnelle, avec un responsable identifié et une trace claire de la suite.',
    icon: <ClipboardList className="size-5" />,
  },
]

const ROLE_CARDS = [
  {
    eyebrow: 'Managers',
    title: 'Décider plus vite, avec moins de bruit.',
    description:
      'Houston aide à prioriser, coordonner et valider sans s’appuyer sur des échanges éphémères comme seule mémoire du terrain.',
    icon: <ShieldCheck className="size-5" />,
  },
  {
    eyebrow: 'Équipes terrain',
    title: 'Faire remonter une observation qui débouche sur une vraie suite.',
    description:
      'Le terrain n’est plus seulement un flux de messages. Il devient une matière opérationnelle partagée et actionnable.',
    icon: <MessagesSquare className="size-5" />,
  },
]

export function LandingPage() {
  useEffect(() => {
    const previousTitle = document.title
    const descriptionElement = document.querySelector('meta[name="description"]')
    const previousDescription = descriptionElement?.getAttribute('content') ?? null

    document.title = 'Houston | Plateforme opérationnelle pour équipes terrain'

    if (descriptionElement) {
      descriptionElement.setAttribute(
        'content',
        'Houston aide les équipes terrain à transformer des observations brutes en suivi opérationnel structuré.',
      )
    }

    return () => {
      document.title = previousTitle

      if (descriptionElement) {
        if (previousDescription) {
          descriptionElement.setAttribute('content', previousDescription)
        } else {
          descriptionElement.removeAttribute('content')
        }
      }
    }
  }, [])

  return (
    <div className="landing-page min-h-screen overflow-x-hidden bg-[#090909] text-white">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,_rgba(214,59,45,0.18),_rgba(9,9,9,0)_30%),linear-gradient(180deg,_#090909_0%,_#090909_42%,_#0d0d0d_100%)]" />
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:linear-gradient(180deg,rgba(0,0,0,0.7),transparent_88%)]" />

      <LandingNavbar />
      <main>
        <LandingHero />

        <LandingSection
          eyebrow="Le constat"
          title="Une opération ne s’améliore pas quand l’information reste bloquée dans le bruit."
          description="Houston s’adresse aux équipes terrain qui doivent transformer des faits dispersés en suivi clair, responsable et partageable."
        >
          <div className="grid gap-4 lg:grid-cols-2">
            {CONSTAT_CARDS.map((card) => (
              <LandingCard key={card.title} {...card} className="min-h-[15rem]" />
            ))}
          </div>
        </LandingSection>

        <LandingSection
          eyebrow="Le modèle Houston"
          title="Une boucle opérationnelle pensée pour passer du constat à l’exécution."
          description="Le produit suit une logique simple: capter, structurer, coordonner, vérifier. Le backend reste l’autorité sur les règles, les transitions et la portée métier."
        >
          <div className="grid gap-4 lg:grid-cols-3">
            {LOOP_CARDS.map((card) => (
              <LandingCard key={card.title} {...card} className="min-h-[17rem]" />
            ))}
          </div>
        </LandingSection>

        <LandingSection
          eyebrow="Vision partagée"
          title="Managers et équipes avancent mieux quand ils regardent la même situation."
          description="Houston aide à maintenir une image opérationnelle commune: ce qui a été observé, ce qui mérite d’être traité, et ce qui a réellement avancé."
        >
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.9fr)]">
            <article className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.9)] sm:p-8">
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[#ff8477]">
                Ce que Houston cherche à rendre possible
              </p>
              <h3 className="mt-4 max-w-2xl text-[1.85rem] font-semibold tracking-[-0.06em] text-white sm:text-[2.4rem] sm:leading-[1.04]">
                Moins de messages à interpréter. Plus de situations cadrées, d’actions visibles et de validation claire.
              </h3>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-white/66 sm:text-base">
                La promesse n’est pas de multiplier les outils autour du travail. Elle est de donner un
                cadre unique pour comprendre le terrain, coordonner la réponse et garder une trace
                fiable de ce qui a été traité.
              </p>

              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                {[
                  'Moins d’ambiguïté sur la priorité',
                  'Plus de responsabilité sur la suite',
                  'Une lecture plus commune de l’état du terrain',
                ].map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-white/10 bg-[#101010] px-4 py-4 text-sm leading-6 text-white/74"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </article>

            <div className="grid gap-4">
              {ROLE_CARDS.map((card) => (
                <LandingCard key={card.title} {...card} className="min-h-[15rem]" />
              ))}
            </div>
          </div>
        </LandingSection>

        <LandingSection
          id="demo"
          eyebrow="Démo"
          title="Voir Houston sur un cas terrain concret."
          description="La page reste volontairement légère à ce stade. Si le cadre vous parle, le prochain pas est simplement une démonstration du produit et de sa logique opérationnelle."
          className="border-b-0"
        >
          <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(214,59,45,0.15),rgba(255,255,255,0.03))] p-6 shadow-[0_30px_100px_-56px_rgba(0,0,0,0.95)] sm:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl">
                <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[#ff9a90]">
                  Demander une démo
                </p>
                <h3 className="mt-4 text-[2rem] font-semibold tracking-[-0.06em] text-white sm:text-[2.9rem] sm:leading-[1.02]">
                  Clarifier le terrain. Mieux coordonner la suite.
                </h3>
                <p className="mt-4 text-sm leading-7 text-white/70 sm:text-base">
                  Houston vise une exploitation plus lisible, plus structurée et plus responsable. La
                  démonstration sert à vérifier si cette approche colle à votre réalité opérationnelle.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  asChild
                  size="lg"
                  className="h-11 rounded-full border border-[#ff6a5f]/40 bg-[#d63b2d] px-5 text-sm font-semibold text-white hover:bg-[#c43225]"
                >
                  <a href="#demo">
                    Demander une démo
                    <ArrowRight className="size-4" />
                  </a>
                </Button>

                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="h-11 rounded-full border-white/14 bg-white/[0.03] px-5 text-sm font-semibold text-white hover:bg-white/[0.08] hover:text-white"
                >
                  <LandingPathLink href="/login">Se connecter</LandingPathLink>
                </Button>
              </div>
            </div>
          </div>
        </LandingSection>
      </main>
    </div>
  )
}
