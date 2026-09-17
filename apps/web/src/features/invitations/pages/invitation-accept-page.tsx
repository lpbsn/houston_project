import { LoaderCircle } from 'lucide-react'
import { useLayoutEffect, useState } from 'react'

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
import {
  InvitationAcceptApiError,
  acceptDirectorInvitation,
} from '@/features/invitations/api'
import { CURRENT_TERMS_VERSION } from '@/lib/legal'

type InvitationAcceptPageProps = {
  onAccepted: () => void
}

function getAcceptErrorMessage(error: unknown) {
  if (error instanceof InvitationAcceptApiError) {
    return error.message
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return 'Invitation could not be accepted.'
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

  useLayoutEffect(() => {
    if (!fragmentToken) {
      return
    }
    navigate('/invitations', { replace: true })
  }, [fragmentToken, navigate])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFieldError(null)
    setSubmitError(null)

    const invitationToken = token.trim()
    if (!invitationToken) {
      return
    }

    if (!canSubmitPasswordCreation(password, passwordConfirmation)) {
      setFieldError(
        passwordCreationBlockerMessage(
          evaluatePasswordCreation(password, passwordConfirmation),
        ) ?? 'Password and confirmation are required.',
      )
      return
    }

    setIsSubmitting(true)

    try {
      await acceptDirectorInvitation(invitationToken, {
        password,
        password_confirmation: passwordConfirmation,
        ...(acceptTerms ? { terms_version: CURRENT_TERMS_VERSION } : {}),
      })

      onAccepted()
    } catch (error) {
      setSubmitError(getAcceptErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    return (
      <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
        <CardHeader className="gap-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Accept invitation
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            This invitation link is missing or invalid. Open the link from your email to continue.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            className="h-11 w-full rounded-[1rem] sm:w-auto"
            onClick={() => navigate('/login')}
          >
            Sign in
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-2">
        <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
          Accept invitation
        </CardTitle>
        <CardDescription className="text-sm leading-6">
          Set a password to activate your account and join this establishment.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <PasswordCreationFields
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

          {fieldError ? <p className="text-sm text-destructive">{fieldError}</p> : null}
          {submitError ? <p className="text-sm text-destructive">{submitError}</p> : null}

          <Button
            type="submit"
            disabled={isSubmitting}
            className="h-11 w-full rounded-[1rem] sm:w-auto"
          >
            {isSubmitting ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Activating account...
              </>
            ) : (
              'Accept invitation'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
