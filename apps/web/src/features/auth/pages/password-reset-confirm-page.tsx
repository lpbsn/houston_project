import { useLayoutEffect, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AuthApiError, confirmPasswordReset } from '@/features/auth/api'
import { PasswordCreationFields } from '@/features/auth/components/password-creation-fields'
import {
  canSubmitPasswordCreation,
  evaluatePasswordCreation,
  passwordCreationBlockerMessage,
} from '@/features/auth/lib/password-creation'

function getConfirmErrorMessage(error: unknown) {
  if (error instanceof AuthApiError) {
    if (error.code === 'password_reset_invalid') {
      return 'Ce lien n’est plus valide.'
    }
    return error.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'La réinitialisation a échoué.'
}

export function PasswordResetConfirmPage() {
  const { hash, navigate } = useAppRoute()
  const { isAuthenticated, logout } = useAuth()
  const fragmentToken = hash.trim()
  const [token] = useState(fragmentToken)
  const stripped = useRef(false)
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [status, setStatus] = useState<'form' | 'success' | 'error'>(
    fragmentToken ? 'form' : 'error',
  )
  const [error, setError] = useState<string | null>(
    fragmentToken ? null : 'Ouvrez le lien reçu par e-mail pour choisir un nouveau mot de passe.',
  )

  useLayoutEffect(() => {
    if (!fragmentToken || stripped.current) {
      return
    }
    stripped.current = true
    navigate('/password-reset', { replace: true })
  }, [fragmentToken, navigate])

  async function submit() {
    if (!token) {
      return
    }
    const blocker = passwordCreationBlockerMessage(
      evaluatePasswordCreation(password, confirmation),
    )
    if (blocker) {
      setError(blocker)
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await confirmPasswordReset({
        token,
        password,
        password_confirmation: confirmation,
      })
      if (isAuthenticated) {
        await logout()
      }
      setStatus('success')
    } catch (caught) {
      setError(getConfirmErrorMessage(caught))
      setStatus('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
      <CardHeader className="gap-2">
        <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
          Nouveau mot de passe
        </CardTitle>
        <CardDescription className="text-sm leading-6">
          {status === 'success'
            ? 'Votre mot de passe a été mis à jour. Connectez-vous avec le nouveau mot de passe.'
            : error && status === 'error'
              ? error
              : 'Choisissez un nouveau mot de passe, puis reconnectez-vous.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === 'form' ? (
          <>
            <PasswordCreationFields
              password={password}
              confirmation={confirmation}
              onPasswordChange={setPassword}
              onConfirmationChange={setConfirmation}
              disabled={isSubmitting}
            />
            {error && status === 'form' ? (
              <p className="text-sm text-[#E24B4A]">{error}</p>
            ) : null}
            <Button
              type="button"
              className="h-11 w-full rounded-[1rem]"
              disabled={!canSubmitPasswordCreation(password, confirmation) || isSubmitting}
              onClick={() => {
                void submit()
              }}
            >
              {isSubmitting ? 'Enregistrement...' : 'Enregistrer'}
            </Button>
          </>
        ) : (
          <Button
            type="button"
            className="h-11 w-full rounded-[1rem]"
            onClick={() => navigate('/login')}
          >
            Se connecter
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
