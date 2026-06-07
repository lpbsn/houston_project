import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  InvitationAcceptApiError,
  acceptDirectorInvitation,
} from '@/features/invitations/api'

type InvitationAcceptPageProps = {
  token: string
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

export function InvitationAcceptPage({ token, onAccepted }: InvitationAcceptPageProps) {
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFieldError(null)
    setSubmitError(null)

    if (!password || !passwordConfirmation) {
      setFieldError('Password and confirmation are required.')
      return
    }

    if (password !== passwordConfirmation) {
      setFieldError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)

    try {
      await acceptDirectorInvitation(token, {
        password,
        password_confirmation: passwordConfirmation,
      })

      onAccepted()
    } catch (error) {
      setSubmitError(getAcceptErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
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
          <div className="space-y-2">
            <label className="text-sm font-semibold" htmlFor="invitation-password">
              Password
            </label>
            <Input
              id="invitation-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setFieldError(null)
                setSubmitError(null)
              }}
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold" htmlFor="invitation-password-confirmation">
              Confirm password
            </label>
            <Input
              id="invitation-password-confirmation"
              type="password"
              autoComplete="new-password"
              value={passwordConfirmation}
              onChange={(event) => {
                setPasswordConfirmation(event.target.value)
                setFieldError(null)
                setSubmitError(null)
              }}
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            />
          </div>

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
