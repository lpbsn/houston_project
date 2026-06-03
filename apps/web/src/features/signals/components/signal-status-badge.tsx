import { Badge } from '@/components/ui/badge'

type SignalStatusBadgeProps = {
  status: string
}

const LABELS: Record<string, string> = {
  open: 'Ouvert',
  in_progress: 'En cours',
}

export function SignalStatusBadge({ status }: SignalStatusBadgeProps) {
  const label = LABELS[status] ?? status
  return (
    <Badge variant="outline" className="rounded-full border-[#e7dfd1] bg-[#fffaf2] text-[#4a4034]">
      {label}
    </Badge>
  )
}
