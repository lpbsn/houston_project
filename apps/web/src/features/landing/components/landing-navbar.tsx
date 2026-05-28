import { ArrowUpRight } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { LandingPathLink } from '@/features/landing/components/landing-path-link'

export function LandingNavbar() {
  return (
    <header className="landing-navbar sticky top-0 z-20 border-b border-white/10 bg-[#090909]/85 backdrop-blur-xl">
      <div className="mx-auto flex h-18 w-full max-w-7xl items-center justify-between gap-3 px-4 sm:gap-4 sm:px-6 lg:px-8">
        <LandingPathLink
          href="/"
          className="inline-flex items-center gap-3 text-white transition-opacity hover:opacity-85"
          aria-label="Houston landing page"
        >
          <span className="flex size-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-sm font-semibold tracking-[0.28em] text-[#ff6a5f]">
            H
          </span>
          <span className="text-base font-semibold tracking-[0.12em] text-white uppercase sm:text-lg sm:tracking-[0.14em]">
            Houston
          </span>
        </LandingPathLink>

        <nav className="flex items-center gap-2 sm:gap-3">
          <Button
            asChild
            variant="ghost"
            className="rounded-full px-3 text-[0.82rem] font-medium text-white/78 hover:bg-white/[0.06] hover:text-white sm:text-sm"
          >
            <LandingPathLink href="/login">Se connecter</LandingPathLink>
          </Button>

          <Button
            asChild
            size="lg"
            className="h-10 rounded-full border border-[#ff6a5f]/40 bg-[#d63b2d] px-3 text-[0.82rem] font-semibold text-white hover:bg-[#c43225] sm:px-4 sm:text-sm"
          >
            <a href="#demo">
              <span className="sm:hidden">Démo</span>
              <span className="hidden sm:inline">Demander une démo</span>
              <ArrowUpRight className="size-4" />
            </a>
          </Button>
        </nav>
      </div>
    </header>
  )
}
