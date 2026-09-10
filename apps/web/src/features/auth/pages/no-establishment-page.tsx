import { Building2 } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CreateEstablishmentAction } from '@/features/organization/components/create-establishment-action'
import type { BootstrapResponse } from '@/features/auth/types'

type NoEstablishmentPageProps = {
  bootstrap: BootstrapResponse | null | undefined
  navigate: (path: string, options?: { replace?: boolean }) => void
}

export function NoEstablishmentPage({ bootstrap, navigate }: NoEstablishmentPageProps) {
  return (
    <Card className="mx-auto w-full max-w-2xl rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3 text-[color:var(--primary)]">
          <span className="rounded-full bg-[color:var(--primary)]/10 p-3">
            <Building2 className="size-5" />
          </span>
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Aucun établissement disponible
          </CardTitle>
        </div>
        <CardDescription className="text-sm leading-6">
          Votre compte est actif, mais aucun établissement opérationnel ou en configuration
          n&apos;est associé pour le moment.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-6 text-muted-foreground">
        <CreateEstablishmentAction
          bootstrap={bootstrap}
          navigate={navigate}
          triggerVariant="organization"
        />
        <p>
          Contactez votre administrateur ou reprenez une invitation si vous venez de rejoindre
          Houston.
        </p>
      </CardContent>
    </Card>
  )
}
