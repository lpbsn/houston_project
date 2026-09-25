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
    </div>
  )
}
