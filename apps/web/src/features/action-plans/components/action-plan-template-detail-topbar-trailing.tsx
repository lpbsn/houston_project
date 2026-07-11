import { Pencil } from 'lucide-react'

import { Button } from '@/components/ui/button'

import { useActionPlanDetailQuery } from '../hooks'
import { canShowActionPlanUpdate } from '../lib/action-plan-permission-hints'

type ActionPlanTemplateDetailTopbarTrailingProps = {
  establishmentId: string
  actionPlanId: string
  onNavigate: (pathname: string) => void
}

export function ActionPlanTemplateDetailTopbarTrailing({
  establishmentId,
  actionPlanId,
  onNavigate,
}: ActionPlanTemplateDetailTopbarTrailingProps) {
  const detailQuery = useActionPlanDetailQuery(establishmentId, actionPlanId)

  if (detailQuery.isLoading || detailQuery.isError || !detailQuery.data) {
    return null
  }

  if (!canShowActionPlanUpdate(detailQuery.data.permission_hints)) {
    return null
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      className="h-10 w-10 shrink-0 rounded-full border-[#E8E6DF] bg-white text-[#1a1a1a] shadow-sm hover:bg-[#F5F4F0]"
      aria-label="Modifier"
      onClick={() => onNavigate(`/action-plans/${actionPlanId}/edit`)}
    >
      <Pencil className="h-4 w-4" aria-hidden />
    </Button>
  )
}
