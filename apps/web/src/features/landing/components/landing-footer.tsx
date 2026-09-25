import sporeMark from '@/features/landing/assets/spore-mark.png'
import { footerContent } from '@/features/landing/content'

export function LandingFooter() {
  return (
    <footer className="sp-wrap sp-footer">
      <div className="sp-logo">
        <img className="sp-brand-img" src={sporeMark} alt="Logo Spore" width={144} height={144} />
        spore
      </div>
      <span>Comprenez vos établissements en quelques secondes.</span>
      <nav className="sp-footer-links" aria-label="Informations">
        <a href={footerContent.loginHref}>{footerContent.loginLabel}</a>
        <a href={footerContent.legalHref}>{footerContent.legalLabel}</a>
        <a href={footerContent.privacyHref}>{footerContent.privacyLabel}</a>
        <a href={footerContent.termsHref}>{footerContent.termsLabel}</a>
        <a href={footerContent.accountDeletionHref}>{footerContent.accountDeletionLabel}</a>
        <a href={footerContent.supportHref}>{footerContent.supportLabel}</a>
      </nav>
    </footer>
  )
}
