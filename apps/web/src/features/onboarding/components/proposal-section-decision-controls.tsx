import { CheckCircle2, LoaderCircle, XCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { DecisionEnum, SectionEnum } from '@/features/onboarding/types'

type ProposalSectionDecisionControlsProps = {
  decisionState: string | undefined
  disabled: boolean
  onDecision: (section: SectionEnum, decision: DecisionEnum) => void
  pendingSection: string | null
  section: SectionEnum
  title: string
}

export function ProposalSectionDecisionControls({
  decisionState,
  disabled,
  onDecision,
  pendingSection,
  section,
  title,
}: ProposalSectionDecisionControlsProps) {
  return (
    <div className="rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9] px-3 py-3">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="text-xs text-muted-foreground">{decisionState ?? 'no decision'}</div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex">
          <Button
            type="button"
            variant="outline"
            className="h-9 rounded-[1rem] border-emerald-200 bg-emerald-50 text-emerald-700"
            disabled={disabled}
            onClick={() => {
              onDecision(section, 'accepted')
            }}
          >
            {pendingSection === `${section}:accepted` ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <CheckCircle2 className="size-4" />
            )}
            Accept
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-9 rounded-[1rem] border-[#ebe2d5] bg-[#fbf7f0]"
            disabled={disabled}
            onClick={() => {
              onDecision(section, 'skipped')
            }}
          >
            {pendingSection === `${section}:skipped` ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <XCircle className="size-4" />
            )}
            Skip
          </Button>
        </div>
      </div>
    </div>
  )
}

export const TAXONOMY_SECTION_DECISIONS = [
  { section: 'operational_modules' as const, title: 'Modules' },
  { section: 'operational_domains' as const, title: 'Domains' },
  { section: 'operational_subjects' as const, title: 'Subjects' },
]
