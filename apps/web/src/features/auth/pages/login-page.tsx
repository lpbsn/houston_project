import { LoaderCircle } from 'lucide-react'

import sporeIconSrc from '@/assets/brand/spore-icon-green.png'
import { useAuth } from '@/app/auth-provider'
import { LoginForm } from '@/features/auth/components/login-form'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type LoginPageProps = {
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

const loginPageClassName = cn(
  'grid min-h-dvh grid-rows-[auto_1fr_auto]',
  'bg-[#F9FAFB]',
  'bg-[radial-gradient(circle_at_bottom_left,rgba(139,92,246,0.06),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(59,130,246,0.06),transparent_40%)]',
)

function LoginPageShell({ children }: { children: React.ReactNode }) {
  return (
    <div data-testid="login-page" className={loginPageClassName}>
      {children}
    </div>
  )
}

export function LoginPage({ onNavigate }: LoginPageProps) {
  const { isReady } = useAuth()

  if (!isReady) {
    return (
      <LoginPageShell>
        <header
          className="flex justify-end px-4 pt-[max(1rem,var(--app-safe-top))] sm:px-6 sm:pt-[max(1.5rem,var(--app-safe-top))]"
          aria-hidden
        />
        <main className="flex flex-col items-center justify-center px-4">
          <div className="flex items-center gap-3 rounded-full border border-[#E8E6DF] bg-white px-4 py-3 text-sm text-[#6B7280]">
            <LoaderCircle className="size-4 animate-spin text-[#114660]" />
            Restauration de votre session…
          </div>
        </main>
        <footer
          className="pb-[max(1.5rem,var(--app-safe-bottom))] text-center text-xs text-[#9CA3AF]"
          aria-hidden
        />
      </LoginPageShell>
    )
  }

  return (
    <LoginPageShell>
      <header className="flex justify-end px-4 pt-[max(1rem,var(--app-safe-top))] sm:px-6 sm:pt-[max(1.5rem,var(--app-safe-top))]">
        <Button
          type="button"
          variant="outline"
          className="h-10 rounded-2xl border-[#E8E6DF] bg-white text-[#111827] hover:bg-[#F9FAFB]"
          onClick={() => {
            onNavigate('/onboarding')
          }}
        >
          Onboarding
        </Button>
      </header>

      <main className="flex flex-col items-center justify-center gap-8 px-4">
        <div className="flex items-center gap-2.5">
          <span className="text-3xl font-bold tracking-tight text-[#111827]">spore</span>
          <img
            src={sporeIconSrc}
            alt=""
            aria-hidden
            className="size-20 object-contain"
          />
        </div>
        <LoginForm />
      </main>

      <footer className="pb-[max(1.5rem,var(--app-safe-bottom))] text-center text-xs text-[#9CA3AF]">
        © 2026 Spore · Terrain-first
      </footer>
    </LoginPageShell>
  )
}
