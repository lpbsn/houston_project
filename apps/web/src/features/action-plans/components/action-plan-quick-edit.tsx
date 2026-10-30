import { useState } from 'react'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { TerrainCard } from '@/components/ui/terrain'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { useActionPlanExecutionDetailQuery } from '../hooks'
import { useActionPlanExecutionEditSubmit } from '../hooks/use-action-plan-execution-edit-submit'
import { hydrateActionPlanExecutionEditForm } from '../lib/action-plan-execution-edit-form'
import { canDefineCrossPoleTasks } from '../lib/action-plan-management-access'
import { resolveVisibleBusinessUnits } from '../lib/resolve-visible-business-units'
import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import { ActionPlanTaskDraftEditor } from './action-plan-task-draft-editor'

/** Same validation, concurrency token and write path as the complete edit page. */
export function ActionPlanQuickEdit({
  execution,
  establishmentId,
  onClose,
}: {
  execution: ActionPlanExecutionDetail
  establishmentId: string
  onClose: () => void
}) {
  const auth = useAuth()
  const role = auth.activeMembership?.role ?? null
  const staffMode = role === 'staff'
  const [form, setForm] = useState(() => hydrateActionPlanExecutionEditForm(execution))
  const [section, setSection] = useState<'information' | 'tasks' | 'planning'>('information')
  const detail = useActionPlanExecutionDetailQuery(establishmentId, execution.id)
  const tree = useBusinessUnitTreeQuery(establishmentId)
  const businessUnits = resolveVisibleBusinessUnits({
    role,
    scopes: auth.activeMembership?.scopes,
    businessUnits: (tree.data?.business_units ?? []).map((unit) => ({
      id: unit.id,
      label: unit.specific_name,
    })),
    filterByScope: role === 'manager' || staffMode,
  })
  const submit = useActionPlanExecutionEditSubmit({
    establishmentId,
    executionId: execution.id,
    canDefineCrossPoleTasks: canDefineCrossPoleTasks(role),
    staffMode,
    membershipId: auth.activeMembership?.id,
    onNavigate: onClose,
    onConflictReload: async () => {
      const fresh = await detail.refetch()
      if (fresh.data) setForm(hydrateActionPlanExecutionEditForm(fresh.data))
    },
  })
  return (
    <TerrainCard className="space-y-4 border-[#134E64]">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void submit.submit(form)
        }}
        className="space-y-4"
      >
        <h2 className="text-base font-semibold text-[#1a1a1a]">Modifier ce plan</h2>
        <fieldset disabled={submit.isSubmitting} className="space-y-4">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Rubrique à modifier">
            {(
              [
                ['information', 'Titre et description'],
                ['tasks', 'Tâches'],
                ['planning', 'Assignés et échéance'],
              ] as const
            ).map(([id, label]) => (
              <Button
                key={id}
                type="button"
                variant={section === id ? 'default' : 'outline'}
                aria-pressed={section === id}
                onClick={() => setSection(id)}
              >
                {label}
              </Button>
            ))}
          </div>
          {section === 'information' && (
            <div className="space-y-3">
              <label className="block text-sm font-medium">
                Titre
                <Input
                  value={form.title}
                  onChange={(event) => setForm({ ...form, title: event.target.value })}
                />
              </label>
              <label className="block text-sm font-medium">
                Description
                <Textarea
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                />
              </label>
            </div>
          )}
          {section === 'tasks' && (
            <>
              {form.treatedTasks.length > 0 && (
                <p className="text-sm text-[#42433F]">
                  Les {form.treatedTasks.length} tâches déjà traitées sont conservées.
                </p>
              )}
              <ActionPlanTaskDraftEditor
                tasks={form.pendingTasks}
                maxTasks={10 - form.treatedTasks.length}
                establishmentId={establishmentId}
                pilotBusinessUnitId={form.pilotBusinessUnitId}
                canDefineCrossPoleTasks={canDefineCrossPoleTasks(role)}
                staffMode={staffMode}
                businessUnits={businessUnits}
                fieldErrors={submit.fieldErrors}
                density="compact"
                onTasksChange={(update) =>
                  setForm((previous) => ({
                    ...previous,
                    pendingTasks:
                      typeof update === 'function' ? update(previous.pendingTasks) : update,
                  }))
                }
              />
            </>
          )}
          {section === 'planning' && (
            <ActionPlanEventPlanningForm
              draft={form.planningDraft}
              establishmentId={establishmentId}
              pilotBusinessUnitId={form.pilotBusinessUnitId}
              fieldErrors={submit.fieldErrors}
              config={{
                canEditAssignees: !staffMode,
                canSchedule: false,
                staffMode,
                showAdvancedChronology: false,
                hideAssignees: false,
                lockChronologyMode: true,
                lockStart: true,
                assigneeActionsEnabled: false,
              }}
              onDraftChange={(update) =>
                setForm((previous) => ({
                  ...previous,
                  planningDraft:
                    typeof update === 'function' ? update(previous.planningDraft) : update,
                }))
              }
            />
          )}
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
          <div className="flex gap-2">
            <Button type="submit">{submit.isSubmitting ? 'Enregistrement…' : 'Enregistrer'}</Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
          </div>
        </fieldset>
      </form>
    </TerrainCard>
  )
}
