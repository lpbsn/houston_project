import { useEffect, useRef } from 'react'

type LandingPricingProps = {
  demoOpen: boolean
  onDemo: () => void
  onCloseDemo: () => void
}

export function LandingPricing({ demoOpen, onDemo, onCloseDemo }: LandingPricingProps) {
  const demoRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!demoOpen || !demoRef.current) return
    const reduceMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    demoRef.current.scrollIntoView?.({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'center',
    })
  }, [demoOpen])

  return (
    <div className="sp-chapter sp-chapter-pricing">
      <section className="sp-wrap sp-section" id="sp-pricing">
        <div className="pricing-intro">
          <div className="sp-eyebrow">Les offres Spore</div>
          <h2>
            Toute l’intelligence du terrain.
            <br />
            <span className="sp-em">À l’échelle de votre exploitation.</span>
          </h2>
          <p>
            L’application pour vos équipes. Les dashboards pour votre pilotage. L’agent IA pour
            analyser et décider.
          </p>
        </div>
        <div className="new-pricegrid">
          <article className="sp-offer">
            <div className="sp-eyebrow">Un établissement</div>
            <h3>Spore Établissement</h3>
            <div className="sp-price">
              590 € <small>HT / mois / établissement</small>
            </div>
            <p className="price-summary">
              Votre exploitation, comprise et pilotée dans un même espace.
            </p>
            <div className="price-block">
              <h4>Application mobile pour vos équipes terrain</h4>
              <p>
                Observations texte, photo et vocal, chat, plans d’action et suivi des résolutions.
              </p>
            </div>
            <div className="price-block">
              <h4>SaaS et dashboards de pilotage</h4>
              <p>
                Sujets récurrents et nouveaux, traitement des observations, délais, échéances,
                retards et qualité des résolutions.
              </p>
            </div>
            <div className="price-block">
              <h4>Agent IA inclus</h4>
              <p>
                Analyse des reportings à travers les données terrain, détection des problèmes et
                signaux faibles, axes d’amélioration et propositions de plans d’action.
              </p>
            </div>
            <ul className="plan-limits">
              <li>
                <strong>50 utilisateurs inclus</strong>
              </li>
              <li>
                <strong>Documents et photos conservés pendant 1 mois</strong>
              </li>
            </ul>
            <button type="button" className="sp-button" onClick={onDemo}>
              Découvrir Spore pour mon établissement ↗
            </button>
          </article>
          <article className="sp-offer group-offer">
            <div className="sp-eyebrow">Groupes &amp; multi-établissements</div>
            <h3>Spore Groupe</h3>
            <div className="sp-price">Sur devis</div>
            <p className="price-summary">
              Une vision de chaque site. Une intelligence à l’échelle de votre groupe.
            </p>
            <div className="price-block">
              <h4>Toute l’offre Établissement</h4>
              <p>
                Application mobile, dashboards et agent IA pour chaque établissement de votre
                réseau.
              </p>
            </div>
            <div className="price-block">
              <h4>Dashboard cross-établissements</h4>
              <p>
                Consolidez les enjeux, comparez les sites et identifiez les établissements qui
                demandent votre attention.
              </p>
            </div>
            <div className="price-block">
              <h4>Fonctions siège</h4>
              <p>
                Pilotez tous vos établissements, coordonnez les responsables et suivez
                l’avancement des plans d’action du groupe.
              </p>
            </div>
            <div className="price-block">
              <h4>Agent IA cross-établissements</h4>
              <p>
                Analysez les reportings du réseau avec leur contexte terrain. Repérez les problèmes
                communs, les différences entre sites et les pistes d’amélioration à partager.
              </p>
            </div>
            <p className="group-terms">
              Tarification selon le nombre d’établissements, leur taille et le périmètre de votre
              organisation.
            </p>
            <button type="button" className="sp-button" onClick={onDemo}>
              Demander un devis groupe ↗
            </button>
          </article>
        </div>
        <div
          id="sp-demo"
          ref={demoRef}
          className="sp-demo"
          hidden={!demoOpen}
          aria-live="polite"
        >
          <strong>Votre démonstration Spore</strong>
          <p>
            Découvrez comment Spore peut vous aider à comprendre votre exploitation et à piloter
            vos actions.
          </p>
          <p className="sp-note">
            La prise de rendez-vous sera disponible ici. Le lien de réservation reste à
            configurer.
          </p>
          <button type="button" className="sp-button sp-smallbutton" id="sp-close" onClick={onCloseDemo}>
            Fermer
          </button>
        </div>
      </section>
    </div>
  )
}
