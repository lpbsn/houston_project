import { useState } from 'react'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainDialog } from '@/components/ui/terrain'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { useActionPlanCreateSubmit } from '../hooks/use-action-plan-create-submit'
import { resolveActionPlanCreateModeConfig } from '../lib/action-plan-create-mode'
import {
  createActionPlanEventPlanningDraft,
  toCreateFormPlanningSlice,
  isAllDayPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import {
  createActionPlanAssigneeDraft,
  type ActionPlanTaskDraft,
} from '../lib/action-plan-form-validation'
import { resolveVisibleBusinessUnits } from '../lib/resolve-visible-business-units'
import { ActionPlanTaskDraftEditor } from './action-plan-task-draft-editor'
import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'

export function ActionPlanQuickCreate({
  onClose,
  onNavigate,
}: {
  onClose: () => void
  onNavigate: (path: string) => void
}) {
  const auth = useAuth()
  const member = auth.activeMembership
  const establishmentId = member?.establishment_id ?? ''
  const hints = getBootstrapPermissionHints(auth.bootstrap)
  const config = resolveActionPlanCreateModeConfig({
    mode: 'execution',
    role: member?.role ?? null,
    membershipId: member?.id,
    canCreateActionPlan: hints.can_create_action_plan === true,
  })
  const [title, setTitle] = useState('')
  const [pole, setPole] = useState('')
  const [tasks, setTasks] = useState<ActionPlanTaskDraft[]>([])
  const [draft, setDraft] = useState(createActionPlanEventPlanningDraft)
  const tree = useBusinessUnitTreeQuery(establishmentId)
  const units = resolveVisibleBusinessUnits({
    role: member?.role ?? null,
    scopes: member?.scopes,
    businessUnits: (tree.data?.business_units ?? []).map((unit) => ({
      id: unit.id,
      label: unit.specific_name,
    })),
    filterByScope: config.filterBusinessUnitsByScope,
  })
  const selectedPole = pole || (units.length === 1 ? units[0].id : '')
  const planning =
    config.showStaffSelfAssignee && member
      ? {
          ...draft,
          assignees: [
            createActionPlanAssigneeDraft({
              membershipId: member.id,
              businessUnitId: selectedPole,
              displayName: auth.bootstrap?.user?.username ?? 'Moi',
            }),
          ],
        }
      : draft
  const submit = useActionPlanCreateSubmit({
    establishmentId,
    canDefineCrossPoleTasks: config.canDefineCrossPoleTasks,
    ...(config.showStaffSelfAssignee && member
      ? { staffExecutionMode: { membershipId: member.id, pilotBusinessUnitId: selectedPole } }
      : {}),
    onNavigate: (path) => {
      onClose()
      onNavigate(path)
    },
  })
  return (
    <TerrainDialog open title="Nouveau plan" onClose={onClose} dismissible={!submit.isSubmitting}>
      {!config.canAccess ? (
        <p>Vous ne pouvez pas créer de plan.</p>
      ) : (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            const slice = toCreateFormPlanningSlice(planning)
            void submit.submit(
              {
                title,
                description: '',
                pilotBusinessUnitId: selectedPole,
                requiresValidation: config.defaultRequiresValidation,
                saveToLibrary: false,
                tasks,
                assignees: planning.assignees,
                ...slice,
                allDay: isAllDayPlanningDraft(planning),
              },
              planning,
            )
          }}
        >
          <fieldset disabled={submit.isSubmitting} className="space-y-4">
            <label className="block text-sm font-semibold">
              Que faut-il faire ?
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Ex. Préparer le podium de Noël"
              />
            </label>
            <label className="block text-sm font-semibold">
              Pôle d’activité
              <select
                className="mt-1 min-h-11 w-full rounded-lg border bg-white px-3 text-[#1a1a1a]"
                value={selectedPole}
                onChange={(event) => {
                  setPole(event.target.value)
                  setDraft(createActionPlanEventPlanningDraft())
                  setTasks((previous) =>
                    previous.map((task) => ({
                      ...task,
                      businessUnitId: '',
                      assigneeMembershipId: '',
                      assigneeDisplayName: '',
                      assigneeBusinessUnitIds: [],
                    })),
                  )
                }}
              >
                <option value="">Choisir un pôle</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.label}
                  </option>
                ))}
              </select>
            </label>
            {tree.isError && (
              <p role="alert">
                Les pôles n’ont pas pu être chargés.{' '}
                <button type="button" onClick={() => void tree.refetch()}>
                  Réessayer
                </button>
              </p>
            )}
            <ActionPlanTaskDraftEditor
              tasks={tasks}
              establishmentId={establishmentId}
              pilotBusinessUnitId={selectedPole}
              canDefineCrossPoleTasks={config.canDefineCrossPoleTasks}
              staffMode={config.showStaffSelfAssignee}
              businessUnits={units}
              density="compact"
              fieldErrors={submit.fieldErrors}
              onTasksChange={setTasks}
            />
            <ActionPlanEventPlanningForm
              draft={planning}
              establishmentId={establishmentId}
              pilotBusinessUnitId={selectedPole}
              config={{
                canEditAssignees: !config.showStaffSelfAssignee,
                canSchedule: false,
                staffMode: config.showStaffSelfAssignee,
                hideAssignees: false,
                showAdvancedChronology: false,
                lockChronologyMode: true,
                assigneeActionsEnabled: false,
              }}
              fieldErrors={submit.fieldErrors}
              onDraftChange={setDraft}
            />
            <p className="text-xs text-[#42433F]">
              {config.defaultRequiresValidation
                ? 'La réalisation devra être validée.'
                : 'Vous êtes assigné à ce plan.'}{' '}
              Vous pourrez compléter le plan ensuite.
            </p>
            {Object.keys(submit.fieldErrors).length > 0 && (
              <ul role="alert" className="list-disc pl-5 text-sm text-destructive">
                {[...new Set(Object.values(submit.fieldErrors))].map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            )}
            {submit.submitError && (
              <p role="alert" className="text-sm text-destructive">
                {submit.submitError}
              </p>
            )}
            <Button type="submit" disabled={!selectedPole || !title.trim()}>
              {submit.isSubmitting ? 'Création…' : 'Créer le plan'}
            </Button>
          </fieldset>
        </form>
      )}
    </TerrainDialog>
  )
}
