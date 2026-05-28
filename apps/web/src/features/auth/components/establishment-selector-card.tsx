import { ArrowRight, Building2, LoaderCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { Membership } from '@/features/auth/types'

type EstablishmentSelectorCardProps = {
  errorMessage: string | null
  memberships: Membership[]
  pendingEstablishmentId: string | null
  onSelect: (establishmentId: string) => void
}

export function EstablishmentSelectorCard({
  errorMessage,
  memberships,
  pendingEstablishmentId,
  onSelect,
}: EstablishmentSelectorCardProps) {
  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
          Workspace selection
        </Badge>
        <div className="space-y-2">
          <CardTitle className="text-[1.65rem] font-black tracking-[-0.05em]">
            Choose your establishment
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            This session has multiple active memberships. The backend needs one selected
            establishment before it can expose an active workspace context.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {memberships.map((membership) => {
          const isPending = pendingEstablishmentId === membership.establishment_id

          return (
            <button
              key={membership.id}
              type="button"
              onClick={() => onSelect(membership.establishment_id)}
              disabled={isPending}
              className="flex w-full items-center justify-between rounded-[1.4rem] border border-[#ece5da] bg-white px-4 py-4 text-left shadow-[0_16px_36px_-30px_rgba(46,72,173,0.22)] transition hover:border-[color:var(--primary)]/35 hover:shadow-[0_22px_40px_-30px_rgba(46,72,173,0.28)] disabled:opacity-70"
            >
              <div className="min-w-0 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
                    <Building2 className="size-4" />
                  </span>
                  <span className="truncate text-base font-bold tracking-[-0.03em]">
                    {membership.establishment_name}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
                    {membership.organization_name}
                  </Badge>
                  <Badge className="bg-[color:var(--primary)] text-primary-foreground">
                    {membership.role}
                  </Badge>
                  <Badge variant="outline" className="border-[#ebe2d5] bg-white">
                    {membership.operational_domains.length} domains
                  </Badge>
                </div>
              </div>

              <div className="ml-4 flex items-center gap-2 text-[color:var(--primary)]">
                {isPending ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowRight className="size-4" />}
              </div>
            </button>
          )
        })}

        {errorMessage ? (
          <div className="rounded-[1.2rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
            {errorMessage}
          </div>
        ) : null}

        <Button variant="outline" className="h-11 w-full rounded-[1.2rem]" disabled>
          Backend-owned establishment context
        </Button>
      </CardContent>
    </Card>
  )
}
