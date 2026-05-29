import { CheckCircle2, ClipboardEdit, LoaderCircle } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { ActivityDescriptionResponse } from '@/features/onboarding/types'
import { useSubmitActivityDescription } from '@/features/onboarding/hooks'
import { BlockerList, getOnboardingErrorBlockers, getOnboardingErrorMessage } from './onboarding-state'

type ActivityDescriptionCardProps = {
  activityDescription: ActivityDescriptionResponse | null
  sessionId: string
}

const MIN_DESCRIPTION_LENGTH = 50

export function ActivityDescriptionCard({
  activityDescription,
  sessionId,
}: ActivityDescriptionCardProps) {
  const sourceDescription = activityDescription?.description ?? ''
  const [draftState, setDraftState] = useState({
    draft: sourceDescription,
    sourceDescription,
  })
  const [savedMessage, setSavedMessage] = useState<string | null>(null)
  const submitMutation = useSubmitActivityDescription(sessionId)

  const draft =
    draftState.sourceDescription === sourceDescription ? draftState.draft : sourceDescription
  const trimmedDraft = draft.trim()
  const hasChanges = trimmedDraft !== sourceDescription
  const characterCount = trimmedDraft.length
  const helperText = useMemo(() => {
    if (characterCount === 0) {
      return 'Describe what this establishment does and what teams handle day-to-day.'
    }

    if (characterCount < MIN_DESCRIPTION_LENGTH) {
      return `${MIN_DESCRIPTION_LENGTH - characterCount} more characters recommended before saving.`
    }

    return 'Ready to submit to the backend validation path.'
  }, [characterCount])

  const blockers = getOnboardingErrorBlockers(submitMutation.error)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSavedMessage(null)

    try {
      await submitMutation.mutateAsync({ description: trimmedDraft })
      setSavedMessage('Activity description saved.')
    } catch {
      setSavedMessage(null)
    }
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
            Activity
          </Badge>
          {activityDescription?.validated_at ? (
            <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
              validated
            </Badge>
          ) : null}
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Activity description
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            This text is submitted to the onboarding API. Backend validation remains the authority.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-semibold" htmlFor="activity-description">
              Establishment activity
            </label>
            <textarea
              id="activity-description"
              value={draft}
              onChange={(event) => {
                setDraftState({
                  draft: event.target.value,
                  sourceDescription,
                })
                setSavedMessage(null)
              }}
              placeholder="Example: A hotel operations team coordinating housekeeping, front desk, maintenance, and guest requests across daily shifts."
              className="min-h-36 w-full resize-y rounded-[1.2rem] border border-[#e7dfd1] bg-[#fffdf8] px-4 py-3 text-sm leading-6 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <div className="flex flex-col gap-2 text-xs leading-5 text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
              <span>{helperText}</span>
              <span>{characterCount} characters</span>
            </div>
          </div>

          {submitMutation.error ? (
            <div className="space-y-3 rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
              <div>
                {getOnboardingErrorMessage(
                  submitMutation.error,
                  'Activity description could not be saved.',
                )}
              </div>
              {blockers.length > 0 ? <BlockerList blockers={blockers} /> : null}
            </div>
          ) : null}

          {savedMessage ? (
            <div className="flex items-center gap-2 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <CheckCircle2 className="size-4" />
              {savedMessage}
            </div>
          ) : null}

          <Button
            type="submit"
            className="h-11 w-full rounded-[1rem]"
            disabled={submitMutation.isPending || !hasChanges}
          >
            {submitMutation.isPending ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <ClipboardEdit className="size-4" />
                Save description
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
