import { ArrowRight, LoaderCircle, PlayCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BlockerList, getOnboardingErrorBlockers, getOnboardingErrorMessage } from './onboarding-state'

type OnboardingStartCardProps = {
  establishmentId: string
  error: unknown
  isStarting: boolean
  onStart: () => void
}

export function OnboardingStartCard({
  establishmentId,
  error,
  isStarting,
  onStart,
}: OnboardingStartCardProps) {
  const blockers = getOnboardingErrorBlockers(error)

  return (
    <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-[color:var(--primary)] text-primary-foreground">
            Manual onboarding
          </Badge>
          <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
            Backend-owned session
          </Badge>
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.7rem] font-black tracking-[-0.06em]">
            Start runtime onboarding
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            This opens the setup session for the selected establishment. The API will decide
            whether the current account can start or resume it.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="rounded-[1.2rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
          Establishment id:{' '}
          <span className="break-all font-medium text-foreground">{establishmentId}</span>
        </div>

        {error ? (
          <div className="space-y-3 rounded-[1.2rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
            <div>{getOnboardingErrorMessage(error, 'Onboarding could not be started.')}</div>
            {blockers.length > 0 ? <BlockerList blockers={blockers} /> : null}
          </div>
        ) : null}

        <Button
          type="button"
          className="h-11 w-full rounded-[1rem]"
          disabled={isStarting}
          onClick={onStart}
        >
          {isStarting ? (
            <>
              <LoaderCircle className="size-4 animate-spin" />
              Starting session...
            </>
          ) : (
            <>
              <PlayCircle className="size-4" />
              Start onboarding
              <ArrowRight className="size-4" />
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
