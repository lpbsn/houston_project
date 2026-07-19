import { Pencil } from 'lucide-react'

import { Button } from '@/components/ui/button'

import { useActionPlanExecutionDetailQuery } from '../hooks'
import { canShowActionPlanExecutionUpdate } from '../lib/action-plan-permission-hints'

type ActionPlanExecutionDetailTopbarTrailingProps = {
  establishmentId: string
  executionId: string
  onNavigate: (pathname: string) => void
}

export function ActionPlanExecutionDetailTopbarTrailing({
  establishmentId,
  executionId,
  onNavigate,
}: ActionPlanExecutionDetailTopbarTrailingProps) {
  const detailQuery = useActionPlanExecutionDetailQuery(establishmentId, executionId)

  if (detailQuery.isLoading || detailQuery.isError || !detailQuery.data) {
    return null
  }

  if (!canShowActionPlanExecutionUpdate(detailQuery.data.permission_hints)) {
    return null
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      className="h-10 w-10 shrink-0 rounded-full border-[#E8E6DF] bg-white text-[#1a1a1a] shadow-sm hover:bg-[#F5F4F0]"
      aria-label="Modifier"
      onClick={() => onNavigate(`/action-plans/executions/${executionId}/edit`)}
    >
      <Pencil className="h-4 w-4" aria-hidden />
    </Button>
  )
}
