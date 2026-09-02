import { LoaderCircle, UserRound } from 'lucide-react'
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
import { TermsAcceptCheckbox } from '@/features/auth/components/terms-accept-checkbox'
import { CURRENT_TERMS_VERSION } from '@/lib/legal'
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
  const [acceptTerms, setAcceptTerms] = useState(false)
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
        ...(acceptTerms ? { terms_version: CURRENT_TERMS_VERSION } : {}),
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
      className="mx-auto w-full max-w-[96rem] px-4 pb-16 pt-6 sm:px-8 sm:pb-20 lg:px-10"
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
        className="mx-auto max-w-2xl space-y-5 rounded-2xl border border-spore-forest/10 bg-white p-5 sm:p-6"
        onSubmit={handleSubmit}
      >
        <div className="flex items-start gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-spore-forest text-white">
            <UserRound className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-spore-forest">Compte propriétaire</h2>
            <p className="mt-1 text-sm text-spore-muted">
              Créez l’accès owner qui pilotera l’organisation.
            </p>
          </div>
        </div>

        <label className="block space-y-1.5" htmlFor="invite_code">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Code d’invitation
          </span>
          <Input
            id="invite_code"
            autoComplete="off"
            value={form.invite_code}
            onChange={(event) => updateField('invite_code', event.target.value)}
            placeholder="Entrez votre code d’invitation"
            className="h-11 rounded-xl border-spore-forest/15"
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5" htmlFor="first_name">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
              Prénom
            </span>
            <Input
              id="first_name"
              autoComplete="given-name"
              value={form.first_name}
              onChange={(event) => updateField('first_name', event.target.value)}
              className="h-11 rounded-xl border-spore-forest/15"
              required
            />
          </label>
          <label className="block space-y-1.5" htmlFor="last_name">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
              Nom
            </span>
            <Input
              id="last_name"
              autoComplete="family-name"
              value={form.last_name}
              onChange={(event) => updateField('last_name', event.target.value)}
              className="h-11 rounded-xl border-spore-forest/15"
              required
            />
          </label>
        </div>

        <label className="block space-y-1.5" htmlFor="email">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            E-mail
          </span>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(event) => updateField('email', event.target.value)}
            placeholder="vous@exemple.com"
            className="h-11 rounded-xl border-spore-forest/15"
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5" htmlFor="password">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
              Mot de passe
            </span>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={(event) => updateField('password', event.target.value)}
              className="h-11 rounded-xl border-spore-forest/15"
              required
            />
          </label>

          <label className="block space-y-1.5" htmlFor="password_confirmation">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
              Confirmer le mot de passe
            </span>
            <Input
              id="password_confirmation"
              type="password"
              autoComplete="new-password"
              value={form.password_confirmation}
              onChange={(event) => updateField('password_confirmation', event.target.value)}
              className="h-11 rounded-xl border-spore-forest/15"
              required
            />
          </label>
        </div>

        <label className="block space-y-1.5" htmlFor="organization_name">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Nom de l’organisation
          </span>
          <Input
            id="organization_name"
            value={form.organization_name}
            onChange={(event) => updateField('organization_name', event.target.value)}
            className="h-11 rounded-xl border-spore-forest/15"
            required
          />
        </label>

        <TermsAcceptCheckbox checked={acceptTerms} onCheckedChange={setAcceptTerms} />

        {fieldError ? (
          <div
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            data-testid="owner-org-error"
          >
            {fieldError}
          </div>
        ) : null}

        {showLoginCta ? (
          <Button
            type="button"
            variant="outline"
            className="h-11 w-full rounded-xl border-spore-forest/15 bg-white"
            data-testid="owner-org-login-cta"
            onClick={() => onNavigate?.('/login')}
          >
            Se connecter
          </Button>
        ) : null}

        <Button
          className="h-11 w-full rounded-xl bg-spore-forest text-white hover:bg-spore-moss disabled:bg-spore-moss/40"
          disabled={isSubmitting}
          type="submit"
        >
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
