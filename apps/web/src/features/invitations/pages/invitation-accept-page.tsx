import { CheckCircle2, LoaderCircle } from 'lucide-react'
import { useLayoutEffect, useState } from 'react'

import sporeIcon from '@/assets/brand/spore-icon-green.png'

import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { TermsAcceptCheckbox } from '@/features/auth/components/terms-accept-checkbox'
import { PasswordCreationFields } from '@/features/auth/components/password-creation-fields'
import {
  canSubmitPasswordCreation,
  evaluatePasswordCreation,
  passwordCreationBlockerMessage,
} from '@/features/auth/lib/password-creation'
import { clearAuthState, logout } from '@/features/auth/api'
import { getAccessToken } from '@/features/auth/session'
import {
  InvitationAcceptApiError,
  acceptDirectorInvitation,
  previewDirectorInvitation,
} from '@/features/invitations/api'
import { CURRENT_TERMS_VERSION } from '@/lib/legal'

type InvitationAcceptPageProps = {
  onAccepted: () => void
}

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

function InvitationBrand() {
  return (
    <div className="mb-4 flex items-center gap-2 text-[#004d3b]">
      <img src={sporeIcon} alt="" className="size-10 object-contain" />
      <span className="text-3xl font-bold tracking-tight">spore</span>
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
  const [accepted, setAccepted] = useState(false)
  const [needsLogin, setNeedsLogin] = useState(false)
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

      if (outcome.kind === 'membership_only' && outcome.requiresLogin) {
        if (getAccessToken()) {
          setNeedsAccountSwitch(true)
          return
        }
        setNeedsLogin(true)
        setAccepted(true)
        return
      }

      setAccepted(true)
    } catch (error) {
      setSubmitError(getAcceptErrorMessage(error))
    } finally {
      setIsSubmitting(false)
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
      setIsSubmitting(false)
    }
    navigate('/login', { replace: true })
  }

  if (accepted) {
    return (
      <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#dce8e2] bg-white text-[#172e27] shadow-xl">
        <CardHeader className="gap-3">
          <InvitationBrand />
          <CheckCircle2 aria-hidden="true" className="size-12 rounded-full bg-[#edf6f0] p-2 text-[#004d3b]" />
          <CardTitle className="text-2xl font-bold">Bienvenue dans votre équipe !</CardTitle>
          <CardDescription className="text-sm leading-6 text-[#40564d]">
            Votre invitation est acceptée. {needsLogin
              ? 'Connectez-vous avec l’adresse qui a reçu l’invitation pour accéder à votre établissement.'
              : 'Votre espace Spore est prêt.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-2xl bg-[#edf6f0] p-4 text-sm leading-6">
            <p className="font-semibold">Votre première observation compte.</p>
            <p>Une idée, un problème ou un retour client ? Partagez-le avec votre équipe, en texte, photo ou vocal.</p>
          </div>
          <Button className="h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]"
            onClick={() => needsLogin ? navigate('/login', { replace: true }) : onAccepted()}>
            {needsLogin ? 'Se connecter à Spore' : 'Ouvrir mon espace Spore'}
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (needsAccountSwitch) {
    return (
      <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#dce8e2] bg-white text-[#172e27] shadow-[0_20px_60px_-30px_rgba(0,77,59,0.25)]">
        <CardHeader className="gap-2">
          <InvitationBrand />
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Rejoindre mon équipe
          </CardTitle>
          <CardDescription className="text-sm leading-6 text-[#40564d]">
            Votre invitation est acceptée pour un autre compte. Déconnectez-vous de la session actuelle
            puis connectez-vous avec l’adresse qui a reçu l’invitation.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {submitError ? <p role="alert" className="text-sm text-destructive">{submitError}</p> : null}
          <Button
            type="button"
            className="h-12 w-full rounded-[1rem] bg-[#004d3b] text-white hover:bg-[#003b2d]"
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
        </CardContent>
      </Card>
    )
  }

  if (!token) {
    return (
      <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#dce8e2] bg-white text-[#172e27] shadow-[0_20px_60px_-30px_rgba(0,77,59,0.25)]">
        <CardHeader className="gap-2">
          <InvitationBrand />
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Rejoindre mon équipe
          </CardTitle>
          <CardDescription className="text-sm leading-6 text-[#40564d]">
            Ce lien est absent ou invalide. Ouvrez le lien reçu par e-mail pour rejoindre votre équipe.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            className="h-12 w-full rounded-[1rem] bg-[#004d3b] text-white hover:bg-[#003b2d]"
            onClick={() => navigate('/login')}
          >
            Se connecter
          </Button>
        </CardContent>
      </Card>
    )
  }

  const description =
    requiresPassword === false
      ? 'Vous avez déjà un compte Spore. Rejoignez votre équipe en conservant votre mot de passe habituel.'
      : requiresPassword
        ? 'Choisissez votre mot de passe pour activer votre compte et rejoindre votre équipe.'
        : 'Votre invitation n’a pas pu être vérifiée.'

  return (
    <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#dce8e2] bg-white text-[#172e27] shadow-[0_20px_60px_-30px_rgba(0,77,59,0.25)]">
      <CardHeader className="gap-2">
        <InvitationBrand />
        <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
          Rejoindre mon équipe
        </CardTitle>
        <CardDescription className="text-sm leading-6 text-[#40564d]">
          {requiresPassword === null && !submitError
            ? 'Vérification de votre invitation…'
            : description}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {requiresPassword === null && !submitError ? (
          <LoaderCircle className="size-4 animate-spin" />
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

            {fieldError ? <p className="text-sm text-destructive">{fieldError}</p> : null}
            {submitError ? <p role="alert" className="text-sm text-destructive">{submitError}</p> : null}

            <Button
              type="submit"
              disabled={isSubmitting || requiresPassword === null}
              className="h-12 w-full rounded-[1rem] bg-[#004d3b] text-white hover:bg-[#003b2d]"
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
      </CardContent>
    </Card>
  )
}
