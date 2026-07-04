import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanUseSheet } from '../components/action-plan-use-sheet'
import {
  useActivateActionPlanMutation,
  useActionPlanDetailQuery,
  useDeactivateActionPlanMutation,
  useUpdateActionPlanMutation,
  useUseActionPlanMutation,
} from '../hooks'
import { formatCatalogStatusLabel } from '../lib/action-plan-display'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import {
  canShowActionPlanActivate,
  canShowActionPlanDeactivate,
  canShowActionPlanUpdate,
  canShowActionPlanUse,
} from '../lib/action-plan-permission-hints'

type ActionPlanTemplateDetailPageProps = {
  actionPlanId: string
}

export function ActionPlanTemplateDetailPage({ actionPlanId }: ActionPlanTemplateDetailPageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const detailQuery = useActionPlanDetailQuery(establishmentId, actionPlanId)
  const updateMutation = useUpdateActionPlanMutation(establishmentId ?? '', actionPlanId)
  const activateMutation = useActivateActionPlanMutation(establishmentId ?? '', actionPlanId)
  const deactivateMutation = useDeactivateActionPlanMutation(establishmentId ?? '', actionPlanId)
  const useMutation = useUseActionPlanMutation(establishmentId ?? '', actionPlanId)

  const [titleDraft, setTitleDraft] = useState<string | null>(null)
  const [descriptionDraft, setDescriptionDraft] = useState<string | null>(null)
  const [useSheetOpen, setUseSheetOpen] = useState(false)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  if (!establishmentId) {
    return null
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 px-3 py-10 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement du plan...
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveActionPlanErrorMessage(
          detailQuery.error,
          'Ce plan est introuvable ou inaccessible.',
        )}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const plan = detailQuery.data
  const title = titleDraft ?? plan.title
  const description = descriptionDraft ?? plan.description
  const hints = plan.permission_hints
  const canUpdate = canShowActionPlanUpdate(hints)
  const isBusy =
    updateMutation.isPending ||
    activateMutation.isPending ||
    deactivateMutation.isPending ||
    useMutation.isPending

  async function handleSaveMetadata() {
    setFeedback(null)
    try {
      await updateMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
      })
      setTitleDraft(null)
      setDescriptionDraft(null)
      setFeedback({ variant: 'success', message: 'Plan mis à jour.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être mis à jour.'),
      })
    }
  }

  async function handleActivate() {
    setFeedback(null)
    try {
      await activateMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Plan activé dans la bibliothèque.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être activé.'),
      })
    }
  }

  async function handleDeactivate() {
    setFeedback(null)
    try {
      await deactivateMutation.mutateAsync()
      setFeedback({ variant: 'success', message: 'Plan désactivé.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être désactivé.'),
      })
    }
  }

  async function handleUse(body: Parameters<typeof useMutation.mutateAsync>[0]) {
    setFeedback(null)
    try {
      const execution = await useMutation.mutateAsync(body)
      setUseSheetOpen(false)
      navigate(`/action-plans/executions/${execution.id}`)
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveActionPlanErrorMessage(error, 'Le plan n’a pas pu être utilisé.'),
      })
    }
  }

  return (
    <div className="space-y-3 px-3 pb-6 pt-2">
      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      <TerrainCard className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-[#7D7B75]">
            Statut bibliothèque : {formatCatalogStatusLabel(plan.catalog_status)}
          </p>
          <p className="text-xs text-[#7D7B75]">Pôle pilote : {plan.pilot_business_unit.label}</p>
        </div>
        <Input
          value={title}
          onChange={(event) => setTitleDraft(event.target.value)}
          disabled={!canUpdate || isBusy}
          aria-label="Titre du plan"
          className="h-11 border-[#E8E6DF] text-sm font-semibold"
        />
        <textarea
          value={description}
          onChange={(event) => setDescriptionDraft(event.target.value)}
          disabled={!canUpdate || isBusy}
          aria-label="Description"
          className="min-h-20 w-full rounded-xl border border-[#E8E6DF] px-3 py-2 text-sm"
        />
        {canUpdate ? (
          <Button
            type="button"
            variant="outline"
            className="h-10 w-full rounded-xl"
            disabled={isBusy}
            onClick={() => void handleSaveMetadata()}
          >
            Enregistrer
          </Button>
        ) : null}
      </TerrainCard>

      <section className="space-y-2">
        <TerrainSectionLabel>Tâches</TerrainSectionLabel>
        <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
          {plan.tasks.length === 0 ? (
            <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Aucune tâche.</p>
          ) : (
            plan.tasks.map((task) => (
              <div key={task.id} className="px-3 py-3 text-sm text-[#1a1a1a]">
                <p>{task.task}</p>
                <p className="mt-1 text-xs text-[#7D7B75]">{task.business_unit.label}</p>
              </div>
            ))
          )}
        </TerrainCard>
      </section>

      <div className="flex flex-col gap-2">
        {canShowActionPlanUse(hints) ? (
          <Button
            type="button"
            className="h-11 w-full rounded-xl"
            disabled={isBusy}
            onClick={() => setUseSheetOpen(true)}
          >
            Utiliser
          </Button>
        ) : null}
        {canShowActionPlanActivate(hints) ? (
          <Button
            type="button"
            variant="outline"
            className="h-11 w-full rounded-xl"
            disabled={isBusy}
            onClick={() => void handleActivate()}
          >
            Activer dans la bibliothèque
          </Button>
        ) : null}
        {canShowActionPlanDeactivate(hints) ? (
          <Button
            type="button"
            variant="outline"
            className="h-11 w-full rounded-xl text-[#E24B4A]"
            disabled={isBusy}
            onClick={() => void handleDeactivate()}
          >
            Désactiver
          </Button>
        ) : null}
      </div>

      <ActionPlanUseSheet
        open={useSheetOpen}
        establishmentId={establishmentId}
        pilotBusinessUnitId={plan.pilot_business_unit.id}
        isPending={useMutation.isPending}
        onClose={() => setUseSheetOpen(false)}
        onConfirm={(body) => void handleUse(body)}
      />
    </div>
  )
}
