import sporeMark from '@/features/landing/assets/spore-mark.png'

type LandingHeaderProps = {
  onDemo: () => void
}

export function LandingHeader({ onDemo }: LandingHeaderProps) {
  return (
    <header className="sp-wrap sp-nav">
      <a className="sp-logo" href="#sp-top">
        <img className="sp-brand-img" src={sporeMark} alt="Logo Spore" width={144} height={144} />
        spore
      </a>
      <nav className="sp-navlinks" aria-label="Navigation">
        <a href="#sp-product">Le produit</a>
        <a href="#sp-agent">L’agent</a>
        <a href="#sp-pricing">Les offres</a>
        <button type="button" className="sp-button sp-smallbutton" onClick={onDemo}>
          Demander une démo ↗
        </button>
      </nav>
    </header>
  )
}
