import { ArrowLeft, LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  RegistrationValidationError,
  isRegistrationStep1Error,
  registerOnboarding,
  validateRegistrationOwner,
} from '@/features/auth/api'
import type { RegistrationRequest } from '@/features/auth/types'

type OnboardingRegistrationCardProps = {
  onRegistered: (result: { establishmentId: string; sessionId: string }) => void
}

type RegistrationStep = 1 | 2 | 3

type RegistrationFormState = RegistrationRequest & {
  password_confirmation: string
}

const emptyForm: RegistrationFormState = {
  invite_code: '',
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  password_confirmation: '',
  organization_name: '',
  establishment_name: '',
}

const stepMeta: Record<
  RegistrationStep,
  { title: string; description: string; action: string }
> = {
  1: {
    title: 'Compte propriétaire',
    description: 'Saisissez votre code d’invitation et vos informations de connexion.',
    action: 'Continuer',
  },
  2: {
    title: 'Organisation',
    description: 'Nommez l’organisation que vous configurez.',
    action: 'Continuer',
  },
  3: {
    title: 'Établissement',
    description: 'Nommez votre premier établissement pour terminer l’inscription.',
    action: 'Démarrer l’onboarding',
  },
}

function getRegistrationErrorMessage(error: unknown) {
  if (error instanceof RegistrationValidationError) {
    return error.message
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return 'Registration could not be completed.'
}

export function OnboardingRegistrationCard({ onRegistered }: OnboardingRegistrationCardProps) {
  const [step, setStep] = useState<RegistrationStep>(1)
  const [form, setForm] = useState<RegistrationFormState>(emptyForm)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isValidatingOwner, setIsValidatingOwner] = useState(false)

  const meta = stepMeta[step]

  function updateField<K extends keyof RegistrationFormState>(
    key: K,
    value: RegistrationFormState[K],
  ) {
    setForm((current) => ({ ...current, [key]: value }))
    setFieldError(null)
    setSubmitError(null)
  }

  function validateStep1() {
    const inviteCode = form.invite_code.trim()
    const firstName = form.first_name.trim()
    const lastName = form.last_name.trim()
    const email = form.email.trim()
    const password = form.password
    const passwordConfirmation = form.password_confirmation

    if (!inviteCode || !firstName || !lastName || !email || !password || !passwordConfirmation) {
      setFieldError('All fields are required.')
      return false
    }

    if (password !== passwordConfirmation) {
      setFieldError('Passwords do not match.')
      return false
    }

    return true
  }

  function validateStep2() {
    if (!form.organization_name.trim()) {
      setFieldError('Organization name is required.')
      return false
    }

    return true
  }

  function validateStep3() {
    if (!form.establishment_name.trim()) {
      setFieldError('Establishment name is required.')
      return false
    }

    return true
  }

  async function handleContinue(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFieldError(null)
    setSubmitError(null)

    if (step === 1) {
      if (!validateStep1()) {
        return
      }

      setIsValidatingOwner(true)

      try {
        await validateRegistrationOwner({
          invite_code: form.invite_code.trim(),
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          email: form.email.trim(),
          password: form.password,
          password_confirmation: form.password_confirmation,
        })
        setStep(2)
      } catch (error) {
        setFieldError(getRegistrationErrorMessage(error))
      } finally {
        setIsValidatingOwner(false)
      }

      return
    }

    if (step === 2) {
      if (!validateStep2()) {
        return
      }

      setStep(3)
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFieldError(null)
    setSubmitError(null)

    if (!validateStep3()) {
      return
    }

    const payload: RegistrationRequest = {
      invite_code: form.invite_code.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      password: form.password,
      password_confirmation: form.password_confirmation,
      organization_name: form.organization_name.trim(),
      establishment_name: form.establishment_name.trim(),
    }

    setIsSubmitting(true)

    try {
      const response = await registerOnboarding(payload)
      onRegistered({
        establishmentId: response.establishment_id,
        sessionId: response.onboarding_session_id,
      })
    } catch (error) {
      if (isRegistrationStep1Error(error)) {
        setStep(1)
        setFieldError(getRegistrationErrorMessage(error))
        return
      }

      setSubmitError(getRegistrationErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleBack() {
    setFieldError(null)
    setSubmitError(null)
    setStep((current) => (current > 1 ? ((current - 1) as RegistrationStep) : current))
  }

  return (
    <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Step {step} of 3
          </span>
        </div>
        <div className="space-y-2">
          <CardTitle className="text-[1.7rem] font-black tracking-[-0.06em]">
            {meta.title}
          </CardTitle>
          <CardDescription className="text-sm leading-6">{meta.description}</CardDescription>
        </div>
      </CardHeader>

      <CardContent>
        <form
          className="space-y-4"
          onSubmit={step === 3 ? handleSubmit : handleContinue}
        >
          {step === 1 ? (
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="invite_code">
                  Invitation code
                </label>
                <Input
                  id="invite_code"
                  autoComplete="off"
                  value={form.invite_code}
                  onChange={(event) => updateField('invite_code', event.target.value)}
                  placeholder="Enter your invitation code"
                  required
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="first_name">
                    First name
                  </label>
                  <Input
                    id="first_name"
                    autoComplete="given-name"
                    value={form.first_name}
                    onChange={(event) => updateField('first_name', event.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="last_name">
                    Last name
                  </label>
                  <Input
                    id="last_name"
                    autoComplete="family-name"
                    value={form.last_name}
                    onChange={(event) => updateField('last_name', event.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="email">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) => updateField('email', event.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="password">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(event) => updateField('password', event.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="password_confirmation">
                  Confirm password
                </label>
                <Input
                  id="password_confirmation"
                  type="password"
                  autoComplete="new-password"
                  value={form.password_confirmation}
                  onChange={(event) => updateField('password_confirmation', event.target.value)}
                  required
                />
              </div>
            </>
          ) : null}

          {step === 2 ? (
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="organization_name">
                Organization name
              </label>
              <Input
                id="organization_name"
                value={form.organization_name}
                onChange={(event) => updateField('organization_name', event.target.value)}
                required
              />
            </div>
          ) : null}

          {step === 3 ? (
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="establishment_name">
                Establishment name
              </label>
              <Input
                id="establishment_name"
                value={form.establishment_name}
                onChange={(event) => updateField('establishment_name', event.target.value)}
                required
              />
            </div>
          ) : null}

          {fieldError ? (
            <div className="rounded-xl border border-rose-300/60 bg-rose-50 px-3 py-2 text-sm text-rose-900">
              {fieldError}
            </div>
          ) : null}

          {submitError ? (
            <div className="rounded-xl border border-rose-300/60 bg-rose-50 px-3 py-2 text-sm text-rose-900">
              {submitError}
            </div>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row">
            {step > 1 ? (
              <Button
                type="button"
                variant="outline"
                className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2] sm:flex-1"
                disabled={isSubmitting || isValidatingOwner}
                onClick={handleBack}
              >
                <ArrowLeft className="size-4" />
                Back
              </Button>
            ) : null}

            <Button
              className="h-11 rounded-[1rem] sm:flex-1"
              disabled={isSubmitting || isValidatingOwner}
              type="submit"
            >
              {isSubmitting ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Starting onboarding...
                </>
              ) : isValidatingOwner ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Validating...
                </>
              ) : (
                meta.action
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
