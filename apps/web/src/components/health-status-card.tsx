import { Activity, AlertTriangle, CheckCircle2, LoaderCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

type HealthStatusCardProps = {
  status?: string
  isPending: boolean
  isError: boolean
  errorMessage?: string
}

export function HealthStatusCard({
  status,
  isPending,
  isError,
  errorMessage,
}: HealthStatusCardProps) {
  const tone = isError ? 'destructive' : status === 'ok' ? 'default' : 'secondary'

  return (
    <Card className="border-border/70 bg-background/85 shadow-none">
      <CardHeader className="space-y-3">
        <Badge variant={tone} className="w-fit">
          API health
        </Badge>
        <CardTitle className="flex items-center gap-2">
          <Activity className="size-4 text-primary" />
          Backend reachability
        </CardTitle>
        <CardDescription>
          The frontend uses TanStack Query and generated OpenAPI typing for this probe.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {isPending ? (
          <div className="flex items-center gap-2 rounded-xl border border-border/70 bg-muted/60 p-3">
            <LoaderCircle className="size-4 animate-spin text-primary" />
            <span>Checking `/api/v1/health/`...</span>
          </div>
        ) : null}

        {!isPending && !isError && status ? (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-300/60 bg-emerald-50 p-3 text-emerald-900">
            <CheckCircle2 className="size-4" />
            <span>API responded with status `{status}`.</span>
          </div>
        ) : null}

        {isError ? (
          <div className="flex items-start gap-2 rounded-xl border border-rose-300/60 bg-rose-50 p-3 text-rose-900">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>{errorMessage ?? 'The health probe failed.'}</span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
