import { Clock3 } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function EstablishmentPendingActivationCard() {
  return (
    <Card className="mx-auto w-full max-w-2xl rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3 text-[color:var(--primary)]">
          <span className="rounded-full bg-[color:var(--primary)]/10 p-3">
            <Clock3 className="size-5" />
          </span>
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Établissement en cours de configuration
          </CardTitle>
        </div>
        <CardDescription className="text-sm leading-6">
          Votre compte est activé. L&apos;établissement est encore en cours de configuration.
          Vous pourrez accéder à l&apos;espace une fois l&apos;activation terminée.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm leading-6 text-muted-foreground">
        Reconnectez-vous après l&apos;activation pour accéder au workspace opérationnel.
      </CardContent>
    </Card>
  )
}
