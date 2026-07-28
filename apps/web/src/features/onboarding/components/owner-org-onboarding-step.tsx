import { LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  RegistrationValidationError,
  login,
  registerOnboarding,
} from '@/features/auth/api'
import { resolvePendingLanding } from '@/features/auth/lib/pending-onboarding'
import { OnboardingStepper } from '@/features/onboarding/components/onboarding-stepper'
import {
  clearRegistrationSessionSnapshot,
  loadRegistrationSessionSnapshot,
  saveRegistrationSessionSnapshot,
} from '@/features/onboarding/lib/registration-session-storage'

type OwnerOrgOnboardingStepProps = {
  onRegistered: (result: { establishmentId: string; sessionId: string }) => void
  onNavigate?: (path: string) => void
}

type FormState = {
  invite_code: string
  first_name: string
  last_name: string
  email: string
  password: string
  password_confirmation: string
  organization_name: string
}

function getErrorMessage(error: unknown) {
  if (error instanceof RegistrationValidationError) {
    return error.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'L’inscription n’a pas pu être terminée.'
}

function isDuplicateEmailError(error: unknown): error is RegistrationValidationError {
  return error instanceof RegistrationValidationError && error.code === 'duplicate_email'
}

export function OwnerOrgOnboardingStep({
  onRegistered,
  onNavigate,
}: OwnerOrgOnboardingStepProps) {
  const [form, setForm] = useState<FormState>(() => {
    const stored = loadRegistrationSessionSnapshot()
    return {
      ...stored,
      password: '',
      password_confirmation: '',
    }
  })
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [showLoginCta, setShowLoginCta] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    saveRegistrationSessionSnapshot({
      invite_code: form.invite_code,
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      organization_name: form.organization_name,
    })
  }, [
    form.email,
    form.first_name,
    form.invite_code,
    form.last_name,
    form.organization_name,
  ])

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }))
    setFieldError(null)
    setShowLoginCta(false)
  }

  function validate(): boolean {
    if (
      !form.invite_code.trim() ||
      !form.first_name.trim() ||
      !form.last_name.trim() ||
      !form.email.trim() ||
      !form.password ||
      !form.password_confirmation ||
      !form.organization_name.trim()
    ) {
      setFieldError('Tous les champs sont obligatoires.')
      return false
    }

    if (form.password !== form.password_confirmation) {
      setFieldError('Les mots de passe ne correspondent pas.')
      return false
    }

    return true
  }

  async function resumeViaLogin(email: string, password: string) {
    const auth = await login({ identifier: email, password })
    const landing = resolvePendingLanding(auth.pending_onboarding_memberships ?? [])

    if (landing.kind !== 'onboarding') {
      throw new Error(
        'Un compte existe déjà. Connectez-vous pour reprendre la configuration.',
      )
    }

    clearRegistrationSessionSnapshot()
    onRegistered({
      establishmentId: landing.pending.establishment_id,
      sessionId: landing.pending.onboarding_session_id ?? '',
    })
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFieldError(null)
    setShowLoginCta(false)

    if (!validate()) {
      return
    }

    const email = form.email.trim()
    const password = form.password

    setIsSubmitting(true)
    try {
      const response = await registerOnboarding({
        invite_code: form.invite_code.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email,
        password,
        password_confirmation: form.password_confirmation,
        organization_name: form.organization_name.trim(),
      })
      clearRegistrationSessionSnapshot()
      onRegistered({
        establishmentId: response.establishment_id,
        sessionId: response.onboarding_session_id,
      })
    } catch (error) {
      if (isDuplicateEmailError(error) && email && password) {
        try {
          await resumeViaLogin(email, password)
          return
        } catch {
          setShowLoginCta(true)
          setFieldError(
            'Un compte existe déjà avec cet e-mail. Connectez-vous pour reprendre.',
          )
          return
        }
      }

      if (isDuplicateEmailError(error)) {
        setShowLoginCta(true)
        setFieldError(
          'Un compte existe déjà avec cet e-mail. Connectez-vous pour reprendre.',
        )
        return
      }

      setFieldError(getErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="mx-auto w-full max-w-[96rem] px-4 pb-28 pt-6 sm:px-8 lg:px-10"
      data-testid="owner-org-onboarding-step"
    >
      <div className="mb-6 space-y-3">
        <span className="inline-flex rounded-full bg-spore-moss/20 px-3 py-1 text-xs font-semibold text-spore-forest">
          ✨ Onboarding Spore
        </span>
        <h1 className="text-3xl font-semibold tracking-tight text-spore-forest sm:text-4xl">
          Créez votre organisation
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-spore-muted sm:text-base">
          Renseignez votre compte propriétaire et le nom de l’organisation. Vous
          configurerez l’établissement à l’étape suivante.
        </p>
      </div>

      <OnboardingStepper current="organization" />

      <form
        className="mx-auto max-w-xl space-y-4 rounded-[1.85rem] border border-[#ece5da] bg-[#fffdf9] p-6 shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]"
        onSubmit={handleSubmit}
      >
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="invite_code">
            Code d’invitation
          </label>
          <Input
            id="invite_code"
            autoComplete="off"
            value={form.invite_code}
            onChange={(event) => updateField('invite_code', event.target.value)}
            placeholder="Entrez votre code d’invitation"
            required
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="first_name">
              Prénom
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
              Nom
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
            E-mail
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(event) => updateField('email', event.target.value)}
            placeholder="vous@exemple.com"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="password">
            Mot de passe
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
            Confirmer le mot de passe
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

        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="organization_name">
            Nom de l’organisation
          </label>
          <Input
            id="organization_name"
            value={form.organization_name}
            onChange={(event) => updateField('organization_name', event.target.value)}
            required
          />
        </div>

        {fieldError ? (
          <div
            className="rounded-xl border border-rose-300/60 bg-rose-50 px-3 py-2 text-sm text-rose-900"
            data-testid="owner-org-error"
          >
            {fieldError}
          </div>
        ) : null}

        {showLoginCta ? (
          <Button
            type="button"
            variant="outline"
            className="h-11 w-full rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            data-testid="owner-org-login-cta"
            onClick={() => onNavigate?.('/login')}
          >
            Se connecter
          </Button>
        ) : null}

        <Button className="h-11 w-full rounded-[1rem]" disabled={isSubmitting} type="submit">
          {isSubmitting ? (
            <>
              <LoaderCircle className="size-4 animate-spin" />
              Création en cours…
            </>
          ) : (
            'Continuer'
          )}
        </Button>
      </form>
    </div>
  )
}
