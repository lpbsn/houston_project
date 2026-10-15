import sporeMark from '@/features/landing/assets/spore-mark.png'
import { APP_LOGIN_URL } from '@/features/landing/content'

export function LandingHeader() {
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
        <div className="sp-navactions">
          <a className="sp-login" href={APP_LOGIN_URL}>
            Se connecter
          </a>
          <a href="#sp-contact" className="sp-button sp-smallbutton">
            Demander une démo ↗
          </a>
        </div>
      </nav>
    </header>
  )
}
