type LandingHeroProps = {
  onDemo: () => void
}

export function LandingHero({ onDemo }: LandingHeroProps) {
  return (
    <div className="sp-chapter sp-chapter-hero">
      <section className="sp-wrap sp-hero" id="sp-top">
        <div className="sp-eyebrow">
          <span className="sp-dot" /> Pour les dirigeants et les équipes multisites
        </div>
        <h1>
          Comprenez vos établissements
          <br />
          <span className="sp-em">en quelques secondes.</span>
        </h1>
        <p className="sp-lead">
          Spore agrège les données terrain de votre exploitation : observations, plans d’action,
          résolutions… Et les croise avec vos chiffres pour vous permettre d’identifier les sujets
          qui méritent votre attention, les causes possibles des écarts et les actions à engager.
        </p>
        <div className="sp-heroactions">
          <button type="button" className="sp-button" onClick={onDemo}>
            Voir Spore en action ↗
          </button>
          <a className="sp-secondary" href="#sp-product">
            Découvrir le fonctionnement ↓
          </a>
        </div>
      </section>

      <section className="sp-wrap sp-kpi-band" aria-label="La valeur de Spore">
        <article>
          <div className="sp-kpi-value">
            10 <span className="sp-kpi-unit">h</span>
          </div>
          <h2>économisées par semaine</h2>
          <p>Sur le traitement des notifications.</p>
          <small>Retour d’expérience du fondateur.</small>
        </article>
        <article>
          <div className="sp-kpi-value">
            100 <span className="sp-kpi-unit">%</span>
          </div>
          <h2>des sujets remontés pris en compte</h2>
          <p>Chaque sujet transmis à Spore est analysé et structuré.</p>
        </article>
        <article>
          <div className="sp-kpi-value">
            3 <span className="sp-kpi-unit">mois</span>
          </div>
          <h2>pour mesurer les progrès</h2>
          <p>Suivez l’évolution de vos indicateurs et l’effet des actions engagées.</p>
        </article>
      </section>
    </div>
  )
}
