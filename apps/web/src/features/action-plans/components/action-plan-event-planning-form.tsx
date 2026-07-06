import { ChevronRight, Plus, Trash2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { TerrainCard, TerrainSectionLabel, TerrainSwitch } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import {
  ACTION_PLAN_RECURRENCE_DAY_LABELS,
  ACTION_PLAN_RECURRENCE_DAYS,
  type ActionPlanRecurrenceDay,
} from '../lib/action-plan-schedule-constants'
import {
  createActionPlanAssigneeDraft,
  type ActionPlanAssigneeDraft,
} from '../lib/action-plan-form-validation'
import {
  combineDateAndTimeToIso,
  formatAssigneeSummary,
  formatRecurrenceDaysSummary,
  snapTimeToFiveMinutes,
  splitIsoToDateAndTime,
  type ActionPlanEventPlanningConfig,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { ActionPlanAssigneesSheet } from './action-plan-assignees-sheet'
import { PlanningDateRow } from './planning/planning-date-row'
import {
  PlanningDateTimeRow,
  type PlanningPickerTarget,
} from './planning/planning-date-time-row'

type ActionPlanEventPlanningFormProps = {
  draft: ActionPlanEventPlanningDraft
  config: ActionPlanEventPlanningConfig
  establishmentId: string
  pilotBusinessUnitId: string
  fieldErrors?: Record<string, string>
  onDraftChange: (draft: ActionPlanEventPlanningDraft) => void
}

type PlanningFormRowProps = {
  label: string
  summary?: string
  onClick?: () => void
  disabled?: boolean
  children?: ReactNode
  error?: string
  className?: string
}

function PlanningFormRow({
  label,
  summary,
  onClick,
  disabled = false,
  children,
  error,
  className,
}: PlanningFormRowProps) {
  const interactive = Boolean(onClick) && !disabled
  const Tag = interactive ? 'button' : 'div'

  return (
    <div className={cn('border-b border-[#E8E6DF] last:border-b-0', className)}>
      <Tag
        type={interactive ? 'button' : undefined}
        className={cn(
          'flex w-full items-center justify-between gap-3 px-3 py-3 text-left',
          interactive && 'active:bg-[#F5F4F0]',
          disabled && 'opacity-60',
        )}
        onClick={interactive ? onClick : undefined}
        disabled={disabled}
      >
        <span className="text-sm text-[#1a1a1a]">{label}</span>
        <span className="flex min-w-0 items-center gap-1.5 text-sm text-[#7D7B75]">
          {summary ? <span className="truncate">{summary}</span> : null}
          {interactive ? <ChevronRight className="size-4 shrink-0" aria-hidden /> : null}
        </span>
      </Tag>
      {children ? <div className="space-y-2 px-3 pb-3">{children}</div> : null}
      {error ? <p className="px-3 pb-2 text-xs text-destructive">{error}</p> : null}
    </div>
  )
}

export function ActionPlanEventPlanningForm({
  draft,
  config,
  establishmentId,
  pilotBusinessUnitId,
  fieldErrors = {},
  onDraftChange,
}: ActionPlanEventPlanningFormProps) {
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)
  const [advancedExpanded, setAdvancedExpanded] = useState(false)
  const [openPicker, setOpenPicker] = useState<PlanningPickerTarget>(null)

  function updateDraft(patch: Partial<ActionPlanEventPlanningDraft>) {
    onDraftChange({ ...draft, ...patch })
  }

  function toggleDay(day: ActionPlanRecurrenceDay) {
    const nextDays = draft.recurrenceDays.includes(day)
      ? draft.recurrenceDays.filter((value) => value !== day)
      : [...draft.recurrenceDays, day]
    updateDraft({ recurrenceDays: nextDays })
  }

  function updateAssignee(id: string, patch: Partial<ActionPlanAssigneeDraft>) {
    updateDraft({
      assignees: draft.assignees.map((assignee) =>
        assignee.id === id ? { ...assignee, ...patch } : assignee,
      ),
    })
  }

  const assigneeSummary = formatAssigneeSummary(draft.assignees, {
    staffMode: config.staffMode,
    staffDisplayName: config.staffDisplayName,
  })

  const showAssignees = !config.hideAssignees
  const canToggleRepeat = config.canSchedule
  const showRepeatFields = draft.repeatEnabled && canToggleRepeat

  return (
    <>
      <section className="space-y-2">
        <TerrainSectionLabel>Planification</TerrainSectionLabel>
        <TerrainCard className="overflow-hidden p-0">
          {showAssignees ? (
            <PlanningFormRow
              label="Assignés"
              summary={assigneeSummary}
              onClick={
                config.canEditAssignees ? () => setAssigneeSheetOpen(true) : undefined
              }
              disabled={!config.canEditAssignees}
              error={fieldErrors.assignees}
            />
          ) : null}

          <TerrainSwitch
            variant="bordered"
            label="Toute la journée"
            checked={draft.allDay}
            onCheckedChange={(allDay) => updateDraft({ allDay })}
          />

          <PlanningDateTimeRow
            rowId="shared-start"
            label="Début"
            date={draft.startDate}
            time={draft.startTime}
            hideTime={draft.allDay}
            openPicker={openPicker}
            onOpenPickerChange={setOpenPicker}
            onDateChange={(startDate) => updateDraft({ startDate })}
            onTimeChange={(startTime) =>
              updateDraft({ startTime: snapTimeToFiveMinutes(startTime) })
            }
            error={fieldErrors.startAt ?? fieldErrors.startTime}
          />

          <PlanningDateTimeRow
            rowId="shared-end"
            label="Fin"
            date={draft.endDate}
            time={draft.endTime}
            hideTime={draft.allDay}
            openPicker={openPicker}
            onOpenPickerChange={setOpenPicker}
            onDateChange={(endDate) => updateDraft({ endDate })}
            onTimeChange={(endTime) =>
              updateDraft({ endTime: snapTimeToFiveMinutes(endTime) })
            }
            error={
              fieldErrors.endDate ??
              fieldErrors.sharedEndAt ??
              fieldErrors.endAt ??
              fieldErrors.endTime
            }
          />

          {canToggleRepeat ? (
            <TerrainSwitch
              variant="bordered"
              label="Répéter"
              checked={draft.repeatEnabled}
              onCheckedChange={(repeatEnabled) => updateDraft({ repeatEnabled })}
            />
          ) : null}

          {showRepeatFields ? (
            <>
              <PlanningDateRow
                rowId="recurrence-end"
                label="Fin de la récurrence"
                date={draft.recurrenceEndDate}
                openPicker={openPicker}
                onOpenPickerChange={setOpenPicker}
                onDateChange={(recurrenceEndDate) => updateDraft({ recurrenceEndDate })}
                error={fieldErrors.recurrenceEndDate}
              />

              <PlanningFormRow
                label="Jours"
                summary={formatRecurrenceDaysSummary(draft.recurrenceDays)}
                error={fieldErrors.recurrenceDays}
              >
                <div className="flex flex-wrap gap-2">
                  {ACTION_PLAN_RECURRENCE_DAYS.map((day) => {
                    const selected = draft.recurrenceDays.includes(day)
                    return (
                      <button
                        key={day}
                        type="button"
                        className={cn(
                          'rounded-full border px-3 py-1 text-xs',
                          selected
                            ? 'border-[#1a1a1a] bg-[#1a1a1a] text-white'
                            : 'border-[#E8E6DF] text-[#1a1a1a]',
                        )}
                        onClick={() => toggleDay(day)}
                      >
                        {ACTION_PLAN_RECURRENCE_DAY_LABELS[day]}
                      </button>
                    )
                  })}
                </div>
                {config.staffMode ? (
                  <p className="text-xs text-[#7D7B75]">
                    La planification récurrente vous sera assignée sur le pôle pilote du modèle.
                  </p>
                ) : null}
              </PlanningFormRow>
            </>
          ) : null}
        </TerrainCard>
      </section>

      {config.showAdvancedChronology ? (
        <section className="space-y-2">
          <button
            type="button"
            className="flex w-full items-center justify-between gap-2 text-left"
            onClick={() => setAdvancedExpanded((value) => !value)}
            aria-expanded={advancedExpanded}
          >
            <TerrainSectionLabel>Chronologie avancée</TerrainSectionLabel>
            <ChevronRight
              className={cn(
                'size-4 shrink-0 text-[#7D7B75] transition-transform',
                advancedExpanded && 'rotate-90',
              )}
            />
          </button>
          {advancedExpanded ? (
            <TerrainCard className="space-y-3 overflow-hidden p-0">
              <TerrainSwitch
                variant="bordered"
                label="Chronologie par assigné"
                checked={draft.usePerAssigneeChronology}
                onCheckedChange={(usePerAssigneeChronology) =>
                  updateDraft({ usePerAssigneeChronology })
                }
              />
              {draft.usePerAssigneeChronology ? (
                <div className="space-y-3 px-3 pb-3">
                  {draft.assignees.map((assignee) => {
                    const startParts = splitIsoToDateAndTime(assignee.startAt)
                    const endParts = splitIsoToDateAndTime(assignee.endAt)
                    return (
                      <div
                        key={assignee.id}
                        className="overflow-hidden rounded-xl border border-[#E8E6DF]"
                      >
                        <div className="flex items-center justify-between gap-2 border-b border-[#E8E6DF] px-3 py-2">
                          <p className="text-sm font-medium text-[#1a1a1a]">
                            {assignee.displayName || 'Assigné'}
                          </p>
                          <button
                            type="button"
                            className="rounded-lg p-2 text-[#E24B4A]"
                            aria-label="Retirer l’assigné"
                            onClick={() =>
                              updateDraft({
                                assignees: draft.assignees.filter(
                                  (candidate) => candidate.id !== assignee.id,
                                ),
                              })
                            }
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-start`}
                          label="Début"
                          date={startParts.date}
                          time={startParts.time}
                          hideTime={false}
                          openPicker={openPicker}
                          onOpenPickerChange={setOpenPicker}
                          onDateChange={(date) =>
                            updateAssignee(assignee.id, {
                              startAt: combineDateAndTimeToIso(
                                date,
                                startParts.time,
                                'start',
                              ),
                            })
                          }
                          onTimeChange={(time) =>
                            updateAssignee(assignee.id, {
                              startAt: combineDateAndTimeToIso(
                                startParts.date,
                                snapTimeToFiveMinutes(time),
                                'start',
                              ),
                            })
                          }
                        />
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-end`}
                          label="Fin"
                          date={endParts.date}
                          time={endParts.time}
                          hideTime={false}
                          openPicker={openPicker}
                          onOpenPickerChange={setOpenPicker}
                          onDateChange={(date) =>
                            updateAssignee(assignee.id, {
                              endAt: combineDateAndTimeToIso(date, endParts.time, 'end'),
                            })
                          }
                          onTimeChange={(time) =>
                            updateAssignee(assignee.id, {
                              endAt: combineDateAndTimeToIso(
                                endParts.date,
                                snapTimeToFiveMinutes(time),
                                'end',
                              ),
                            })
                          }
                        />
                      </div>
                    )
                  })}
                  <Button
                    type="button"
                    variant="outline"
                    className="h-10 w-full rounded-xl border-dashed"
                    onClick={() =>
                      updateDraft({
                        assignees: [
                          ...draft.assignees,
                          createActionPlanAssigneeDraft({ businessUnitId: pilotBusinessUnitId }),
                        ],
                      })
                    }
                  >
                    <Plus className="mr-2 h-4 w-4" aria-hidden />
                    Ajouter un créneau assigné
                  </Button>
                </div>
              ) : null}
            </TerrainCard>
          ) : null}
        </section>
      ) : null}

      {config.canEditAssignees ? (
        <ActionPlanAssigneesSheet
          open={assigneeSheetOpen}
          establishmentId={establishmentId}
          pilotBusinessUnitId={pilotBusinessUnitId}
          assignees={draft.assignees}
          onAssigneesChange={(assignees) => updateDraft({ assignees })}
          onClose={() => setAssigneeSheetOpen(false)}
          onConfirm={() => setAssigneeSheetOpen(false)}
        />
      ) : null}
    </>
  )
}
