import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { AuthApiError, requestPasswordReset } from '@/features/auth/api'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ForgotPasswordPageProps = {
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

const pageClassName = cn(
  'grid min-h-dvh grid-rows-[auto_1fr_auto]',
  'bg-[#F9FAFB]',
)

export function ForgotPasswordPage({ onNavigate }: ForgotPasswordPageProps) {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await requestPasswordReset({ email: email.trim() })
      setSubmitted(true)
    } catch (caught) {
      if (caught instanceof AuthApiError && caught.code === 'password_reset_unavailable') {
        setError('La récupération de mot de passe est indisponible pour le moment.')
      } else {
        setError('La demande n’a pas pu être envoyée.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div data-testid="forgot-password-page" className={pageClassName}>
      <header className="flex justify-end px-4 pt-[max(1rem,var(--app-safe-top))] sm:px-6 sm:pt-[max(1.5rem,var(--app-safe-top))]" />
      <main className="flex flex-col items-center justify-center px-4">
        <section className="w-full max-w-[346px] rounded-[22px] border border-[#E8E6DF] bg-white px-5 py-6 sm:max-w-[360px]">
          <h1 className="text-lg font-semibold text-[#111827]">Mot de passe oublié</h1>
          {submitted ? (
            <p className="mt-4 text-sm text-[#5c5a54]">
              Si un compte existe pour cette adresse, un lien de réinitialisation a été envoyé.
            </p>
          ) : (
            <form className="mt-4 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
              <label className="block space-y-1.5 text-sm font-semibold text-[#111827]" htmlFor="reset-email">
                Email
                <Input
                  id="reset-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  className="h-12 rounded-full"
                />
              </label>
              {error ? <p className="text-sm text-[#E24B4A]">{error}</p> : null}
              <Button
                className={cn(
                  'h-12 w-full rounded-full text-[15px] font-semibold text-white',
                  terrainBrandAction.bg,
                  terrainBrandAction.hover,
                )}
                disabled={isSubmitting || !email.trim()}
                type="submit"
              >
                {isSubmitting ? 'Envoi...' : 'Envoyer le lien'}
              </Button>
            </form>
          )}
          <button
            type="button"
            className="mt-4 w-full text-center text-sm text-[#6B7280]"
            onClick={() => onNavigate('/login')}
          >
            Retour à la connexion
          </button>
        </section>
      </main>
      <footer className="pb-[max(1.5rem,var(--app-safe-bottom))]" />
    </div>
  )
}
