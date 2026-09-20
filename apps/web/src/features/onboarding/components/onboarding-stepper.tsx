import { Check } from 'lucide-react'

export type OnboardingWizardStep = 'organization' | 'structure' | 'team'

const STEPS: Array<{ id: OnboardingWizardStep; label: string }> = [
  { id: 'organization', label: 'Organisation — Owner & infos' },
  { id: 'structure', label: 'Établissement — Infos & pôles' },
  { id: 'team', label: 'Équipe — Membres & rôles' },
]

const ORDER: OnboardingWizardStep[] = ['organization', 'structure', 'team']

function stepIndex(step: OnboardingWizardStep) {
  return ORDER.indexOf(step)
}

export function OnboardingStepper({ current }: { current: OnboardingWizardStep }) {
  const currentIndex = stepIndex(current)

  return (
    <div className="mb-8 flex flex-wrap gap-2" data-testid="onboarding-stepper">
      {STEPS.map((step, index) => {
        const isCurrent = step.id === current
        const isDone = index < currentIndex

        return (
          <div
            key={step.id}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
              isCurrent
                ? 'border-primary/20 bg-primary/10 font-medium text-foreground'
                : 'border-border bg-background text-muted-foreground'
            }`}
            data-testid={`onboarding-step-${step.id}`}
            data-state={isCurrent ? 'current' : isDone ? 'done' : 'upcoming'}
          >
            <span
              className={`flex size-6 items-center justify-center rounded-full text-xs ${
                isDone
                  ? 'bg-primary/15 text-primary'
                  : isCurrent
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
              }`}
            >
              {isDone ? <Check className="size-3.5" /> : String(index + 1)}
            </span>
            {step.label}
          </div>
        )
      })}
    </div>
  )
}
