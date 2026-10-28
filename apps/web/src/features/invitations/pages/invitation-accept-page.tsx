import { CheckCircle2, LoaderCircle } from 'lucide-react'
import { useLayoutEffect, useState } from 'react'

import sporeIconSrc from '@/assets/brand/spore-icon-green.png'
import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { clearAuthState, logout } from '@/features/auth/api'
import { PasswordCreationFields } from '@/features/auth/components/password-creation-fields'
import { TermsAcceptCheckbox } from '@/features/auth/components/terms-accept-checkbox'
import {
  canSubmitPasswordCreation,
  evaluatePasswordCreation,
  passwordCreationBlockerMessage,
} from '@/features/auth/lib/password-creation'
import { getAccessToken } from '@/features/auth/session'
import { rememberAccessArrival, type AccessArrival } from '@/features/install/arrival'
import {
  InvitationAcceptApiError,
  acceptDirectorInvitation,
  previewDirectorInvitation,
} from '@/features/invitations/api'
import { buildLoginRedirectHref } from '@/lib/app-open-target'
import { CURRENT_TERMS_VERSION } from '@/lib/legal'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type InvitationAcceptPageProps = {
  onAccepted: () => void
}

const pageClassName = cn(
  'grid min-h-dvh grid-rows-[auto_1fr_auto]',
  'bg-[#F9FAFB]',
  'bg-[radial-gradient(circle_at_bottom_left,rgba(139,92,246,0.06),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(59,130,246,0.06),transparent_40%)]',
)

const authActionClassName = cn(
  'h-12 w-full rounded-full text-[15px] font-semibold text-white',
  terrainBrandAction.bg,
  terrainBrandAction.hover,
)

function getAcceptErrorMessage(error: unknown) {
  if (error instanceof InvitationAcceptApiError) {
    if (error.code === 'invitation_expired') {
      return 'Cette invitation a expiré. Demandez une nouvelle invitation à votre responsable.'
    }
    if (error.code === 'invitation_already_accepted') {
      return 'Cette invitation a déjà été acceptée. Connectez-vous avec votre compte Spore.'
    }
    if (error.code === 'invitation_invalid') {
      return 'Cette invitation est invalide. Demandez un nouveau lien à votre responsable.'
    }
    return error.message
  }
  return 'Impossible de valider votre invitation. Vérifiez votre connexion puis réessayez.'
}

function InvitationAuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div data-testid="invitation-accept-page" className={pageClassName}>
      <header
        className="flex justify-end px-4 pt-[max(1rem,var(--app-safe-top))] sm:px-6 sm:pt-[max(1.5rem,var(--app-safe-top))]"
        aria-hidden
      />
      <main className="flex flex-col items-center justify-center gap-8 px-4 py-8">
        <div className="flex items-center gap-2.5">
          <span className="text-3xl font-bold tracking-tight text-[#111827]">spore</span>
          <img src={sporeIconSrc} alt="" aria-hidden className="size-20 object-contain" />
        </div>
        {children}
      </main>
      <footer className="pb-[max(1.5rem,var(--app-safe-bottom))] text-center text-xs text-[#9CA3AF]">
        © 2026 Spore · Terrain-first
      </footer>
    </div>
  )
}

function InvitationPanel({
  title,
  description,
  leading,
  children,
}: {
  title: string
  description?: string
  leading?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section className="w-full max-w-lg rounded-[22px] border border-[#E8E6DF] bg-white px-5 py-6 shadow-[0_20px_60px_-24px_rgba(15,23,42,0.12)] sm:rounded-3xl">
      {leading}
      <h1 className="text-lg font-semibold text-[#111827]">{title}</h1>
      {description ? <p className="mt-2 text-sm leading-6 text-[#6B7280]">{description}</p> : null}
      <div className="mt-5 space-y-4">{children}</div>
    </section>
  )
}

function InvitationAlert({ children }: { children: React.ReactNode }) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-rose-300/60 bg-rose-50 px-3 py-2 text-sm text-rose-900"
    >
      {children}
    </div>
  )
}

export function InvitationAcceptPage({ onAccepted }: InvitationAcceptPageProps) {
  const { hash, navigate } = useAppRoute()
  const fragmentToken = hash.trim()
  const [token] = useState(fragmentToken)
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [acceptTerms, setAcceptTerms] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [requiresPassword, setRequiresPassword] = useState<boolean | null>(null)
  const [establishmentName, setEstablishmentName] = useState('')
  const [accepted, setAccepted] = useState(false)
  const [switchArrival, setSwitchArrival] = useState<AccessArrival | null>(null)
  const [needsAccountSwitch, setNeedsAccountSwitch] = useState(false)

  useLayoutEffect(() => {
    if (!fragmentToken) {
      return
    }
    navigate('/invitations', { replace: true })
  }, [fragmentToken, navigate])

  useLayoutEffect(() => {
    const invitationToken = token.trim()
    if (!invitationToken) {
      return
    }

    let cancelled = false
    void previewDirectorInvitation(invitationToken)
      .then((preview) => {
        if (!cancelled) {
          setRequiresPassword(preview.requiresPassword)
          setEstablishmentName(preview.establishmentName?.trim() ?? '')
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setSubmitError(getAcceptErrorMessage(error))
          setRequiresPassword(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [token])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFieldError(null)
    setSubmitError(null)

    const invitationToken = token.trim()
    if (!invitationToken || requiresPassword === null || isSubmitting || accepted) {
      return
    }

    if (requiresPassword && !canSubmitPasswordCreation(password, passwordConfirmation)) {
      setFieldError(
        passwordCreationBlockerMessage(
          evaluatePasswordCreation(password, passwordConfirmation),
        ) ?? 'Saisissez et confirmez votre mot de passe.',
      )
      return
    }

    setIsSubmitting(true)
    let keepFormLocked = false

    try {
      const outcome = await acceptDirectorInvitation(invitationToken, {
        ...(requiresPassword
          ? {
              password,
              password_confirmation: passwordConfirmation,
            }
          : {}),
        ...(acceptTerms ? { terms_version: CURRENT_TERMS_VERSION } : {}),
      })

      const arrival =
        outcome.userId && outcome.establishmentId
          ? {
              userId: outcome.userId,
              establishmentId: outcome.establishmentId,
              arrival: outcome.kind === 'session' ? ('activated' as const) : ('joined' as const),
            }
          : null

      if (outcome.kind === 'membership_only' && outcome.requiresLogin) {
        if (getAccessToken()) {
          setSwitchArrival(arrival)
          setNeedsAccountSwitch(true)
          return
        }
        if (arrival) {
          rememberAccessArrival(arrival)
        }
        setAccepted(true)
        return
      }

      if (arrival) {
        rememberAccessArrival(arrival)
      }
      keepFormLocked = true
      onAccepted()
    } catch (error) {
      setSubmitError(getAcceptErrorMessage(error))
    } finally {
      if (!keepFormLocked) {
        setIsSubmitting(false)
      }
    }
  }

  async function switchToInvitedAccount() {
    setSubmitError(null)
    setIsSubmitting(true)
    try {
      await logout()
    } catch (error) {
      setSubmitError(getAcceptErrorMessage(error))
    } finally {
      clearAuthState()
      if (switchArrival) {
        rememberAccessArrival(switchArrival)
      }
      setIsSubmitting(false)
    }
    navigate(buildLoginRedirectHref({ href: '/acces' }), { replace: true })
  }

  if (accepted) {
    return (
      <InvitationAuthShell>
        <InvitationPanel
          title="Bienvenue dans votre équipe !"
          description="Votre invitation est acceptée. Connectez-vous avec l’adresse qui a reçu l’invitation pour accéder à votre établissement."
          leading={
            <CheckCircle2
              aria-hidden="true"
              className="mb-4 size-12 rounded-full bg-[#F3F4F6] p-2 text-[#114660]"
            />
          }
        >
          <div className="rounded-2xl border border-[#E8E6DF] bg-[#F9FAFB] p-4 text-sm leading-6 text-[#111827]">
            <p className="font-semibold">Votre première observation compte.</p>
            <p>Une idée, un problème ou un retour client ? Partagez-le avec votre équipe, en texte, photo ou vocal.</p>
          </div>
          <Button
            type="button"
            className={authActionClassName}
            onClick={() => navigate(buildLoginRedirectHref({ href: '/acces' }), { replace: true })}
          >
            Se connecter à Spore
          </Button>
        </InvitationPanel>
      </InvitationAuthShell>
    )
  }

  if (needsAccountSwitch) {
    return (
      <InvitationAuthShell>
        <InvitationPanel
          title="Rejoindre mon équipe"
          description="Votre invitation est acceptée pour un autre compte. Déconnectez-vous de la session actuelle puis connectez-vous avec l’adresse qui a reçu l’invitation."
        >
          {submitError ? <InvitationAlert>{submitError}</InvitationAlert> : null}
          <Button
            type="button"
            className={authActionClassName}
            disabled={isSubmitting}
            onClick={() => void switchToInvitedAccount()}
          >
            {isSubmitting ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Déconnexion…
              </>
            ) : (
              'Changer de compte et continuer'
            )}
          </Button>
        </InvitationPanel>
      </InvitationAuthShell>
    )
  }

  if (!token) {
    return (
      <InvitationAuthShell>
        <InvitationPanel
          title="Rejoindre mon équipe"
          description="Ce lien est absent ou invalide. Ouvrez le lien reçu par e-mail pour rejoindre votre équipe."
        >
          <Button type="button" className={authActionClassName} onClick={() => navigate('/login')}>
            Se connecter
          </Button>
        </InvitationPanel>
      </InvitationAuthShell>
    )
  }

  const joinedPlace = establishmentName || 'votre équipe'
  const description =
    requiresPassword === false
      ? `Vous avez déjà un compte Spore. Rejoignez ${joinedPlace} en conservant votre mot de passe habituel.`
      : requiresPassword
        ? `Choisissez votre mot de passe pour activer votre compte et rejoindre ${joinedPlace}.`
        : 'Votre invitation n’a pas pu être vérifiée.'

  return (
    <InvitationAuthShell>
      <InvitationPanel
        title="Rejoindre mon équipe"
        description={
          requiresPassword === null && !submitError
            ? 'Vérification de votre invitation…'
            : description
        }
      >
        {requiresPassword === null && !submitError ? (
          <LoaderCircle className="size-4 animate-spin text-[#114660]" />
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            {requiresPassword ? (
              <>
                <PasswordCreationFields
                  disabled={isSubmitting}
                  password={password}
                  confirmation={passwordConfirmation}
                  onPasswordChange={(value) => {
                    setPassword(value)
                    setFieldError(null)
                    setSubmitError(null)
                  }}
                  onConfirmationChange={(value) => {
                    setPasswordConfirmation(value)
                    setFieldError(null)
                    setSubmitError(null)
                  }}
                  passwordId="invitation-password"
                  confirmationId="invitation-password-confirmation"
                />
                <TermsAcceptCheckbox checked={acceptTerms} onCheckedChange={setAcceptTerms} />
              </>
            ) : null}

            {fieldError ? <p className="text-sm text-[#E24B4A]">{fieldError}</p> : null}
            {submitError ? <InvitationAlert>{submitError}</InvitationAlert> : null}

            <Button
              type="submit"
              disabled={isSubmitting || requiresPassword === null}
              className={authActionClassName}
            >
              {isSubmitting ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Activation en cours…
                </>
              ) : (
                'Rejoindre mon équipe'
              )}
            </Button>
          </form>
        )}
      </InvitationPanel>
    </InvitationAuthShell>
  )
}
