import { Pencil } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { appendExecutionFeedSearch } from '@/features/execution/lib/execution-feed-url-state'

import { useActionPlanExecutionDetailQuery } from '../hooks'
import { canShowActionPlanExecutionUpdate } from '../lib/action-plan-permission-hints'

type ActionPlanExecutionDetailTopbarTrailingProps = {
  establishmentId: string
  executionId: string
  search?: string
  onNavigate: (pathname: string) => void
}

export function ActionPlanExecutionDetailTopbarTrailing({
  establishmentId,
  executionId,
  search = '',
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
      onClick={() =>
        onNavigate(appendExecutionFeedSearch(`/action-plans/executions/${executionId}/edit`, search))
      }
    >
      <Pencil className="h-4 w-4" aria-hidden />
    </Button>
  )
}
