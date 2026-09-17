import { useLayoutEffect, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AuthApiError, confirmEmailChange, fetchBootstrap } from '@/features/auth/api'

function getConfirmErrorMessage(error: unknown) {
  if (error instanceof AuthApiError) {
    if (error.code === 'email_change_invalid') {
      return 'Ce lien de confirmation n’est plus valide.'
    }
    if (error.code === 'email_change_duplicate') {
      return 'Un compte existe déjà pour cette adresse.'
    }
    return error.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'La confirmation a échoué.'
}

export function EmailChangeConfirmPage() {
  const { hash, navigate } = useAppRoute()
  const { isAuthenticated, isReady } = useAuth()
  const fragmentToken = hash.trim()
  const [token] = useState(fragmentToken)
  const started = useRef(false)
  const [status, setStatus] = useState<'pending' | 'success' | 'error'>(
    fragmentToken ? 'pending' : 'error',
  )
  const [email, setEmail] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(
    fragmentToken ? null : 'Ouvrez le lien reçu par e-mail pour confirmer votre adresse.',
  )

  useLayoutEffect(() => {
    if (!fragmentToken) {
      return
    }
    navigate('/email-change', { replace: true })
  }, [fragmentToken, navigate])

  useLayoutEffect(() => {
    if (!token || started.current || !isReady) {
      return
    }
    started.current = true
    void confirmEmailChange(token)
      .then(async (result) => {
        setEmail(result.email)
        setStatus('success')
        if (isAuthenticated) {
          await fetchBootstrap()
        }
      })
      .catch((caught) => {
        setError(getConfirmErrorMessage(caught))
        setStatus('error')
      })
  }, [isAuthenticated, isReady, token])

  return (
    <Card className="mx-auto w-full max-w-lg rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-2">
        <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
          Confirmer l’e-mail
        </CardTitle>
        <CardDescription className="text-sm leading-6">
          {status === 'pending'
            ? 'Validation de votre nouvelle adresse…'
            : status === 'success'
              ? `L’adresse ${email} est maintenant votre identifiant de connexion.`
              : error}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {status === 'success' && !isAuthenticated ? (
          <Button
            type="button"
            className="h-11 w-full rounded-[1rem] sm:w-auto"
            onClick={() => navigate('/login')}
          >
            Se connecter
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}
