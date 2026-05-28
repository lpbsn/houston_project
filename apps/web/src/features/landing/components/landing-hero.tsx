import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, Radar, Workflow } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LandingCard } from '@/features/landing/components/landing-card'
import { LandingPathLink } from '@/features/landing/components/landing-path-link'

const HERO_POINTS = [
  'Observation terrain captée sans friction',
  'Cadre opérationnel partagé par les managers',
  'Suivi visible jusqu’à la validation',
]

export function LandingHero() {
  const shouldReduceMotion = useReducedMotion()
  const motionProps = shouldReduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.55, ease: 'easeOut' as const },
      }

  return (
    <section className="landing-hero relative overflow-hidden border-b border-white/10">
      <div className="absolute inset-x-0 top-[-8rem] h-[18rem] bg-[radial-gradient(circle,_rgba(235,69,53,0.24)_0%,_rgba(235,69,53,0)_70%)] blur-3xl" />
      <div className="absolute right-[-5rem] top-[12rem] h-[22rem] w-[22rem] rounded-full bg-[radial-gradient(circle,_rgba(255,255,255,0.08)_0%,_rgba(255,255,255,0)_70%)] blur-3xl" />

      <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 pb-16 pt-28 sm:px-6 sm:pb-20 sm:pt-32 lg:grid lg:grid-cols-[minmax(0,1fr)_28rem] lg:gap-14 lg:px-8 lg:pb-24">
        <motion.div {...motionProps} className="relative z-10 max-w-3xl">
          <Badge className="border border-white/10 bg-white/[0.06] px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-white/78">
            Phase 1.8 · Landing publique
          </Badge>

          <h1 className="mt-6 text-[2.9rem] font-semibold tracking-[-0.08em] text-white sm:text-[4.4rem] sm:leading-[0.95] lg:text-[5.5rem]">
            Le terrain parle.
            <span className="block text-[#ff6a5f]">Houston le transforme en travail structuré.</span>
          </h1>

          <p className="mt-6 max-w-2xl text-base leading-7 text-white/70 sm:text-lg sm:leading-8">
            Houston aide les équipes terrain à faire remonter l’information brute, à la structurer
            en suivi opérationnel, puis à garder managers et équipes alignés sur la suite à donner.
          </p>

          <ul className="mt-8 grid gap-3 text-sm text-white/74 sm:grid-cols-3 sm:text-[0.95rem]">
            {HERO_POINTS.map((item) => (
              <li
                key={item}
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 backdrop-blur-sm"
              >
                {item}
              </li>
            ))}
          </ul>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="h-11 rounded-full border border-[#ff6a5f]/40 bg-[#d63b2d] px-5 text-sm font-semibold text-white shadow-[0_20px_60px_-30px_rgba(214,59,45,0.95)] hover:bg-[#c43225]"
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
        </motion.div>

        <motion.div
          {...(shouldReduceMotion
            ? {}
            : {
                initial: { opacity: 0, scale: 0.98 },
                animate: { opacity: 1, scale: 1 },
                transition: { duration: 0.65, ease: 'easeOut' as const, delay: 0.12 },
              })}
          className="relative z-10 grid gap-4"
        >
          <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.02))] p-5 shadow-[0_36px_120px_-64px_rgba(0,0,0,0.95)] sm:p-6">
            <div className="rounded-[1.5rem] border border-white/10 bg-[#121212] p-5">
              <div className="flex items-center justify-between text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-white/52">
                <span>Boucle opérationnelle</span>
                <span className="text-[#ff7a6b]">Houston</span>
              </div>

              <div className="mt-6 space-y-3">
                {[
                  'Observation',
                  'Signal',
                  'Action',
                  'Exécution',
                  'Validation',
                ].map((step, index) => (
                  <div
                    key={step}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3"
                  >
                    <div>
                      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-white/42">
                        Étape {index + 1}
                      </p>
                      <p className="mt-1 text-sm font-medium text-white">{step}</p>
                    </div>
                    <div className="size-2 rounded-full bg-[#ff6a5f]" />
                  </div>
                ))}
              </div>

              <p className="mt-5 text-sm leading-6 text-white/58">
                Le produit est conçu pour rendre chaque information terrain lisible, assignable et
                suivie jusqu’au résultat.
              </p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <LandingCard
              eyebrow="Managers"
              title="Coordonner les actions sans piloter dans le bruit."
              description="Houston rend les arbitrages visibles et garde la responsabilité là où elle doit être."
              icon={<Workflow className="size-5" />}
            />
            <LandingCard
              eyebrow="Équipes"
              title="Conserver une image partagée de ce qui se passe réellement."
              description="Les équipes terrain peuvent signaler, suivre et comprendre la suite donnée, sans multiplier les canaux."
              icon={<Radar className="size-5" />}
            />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
