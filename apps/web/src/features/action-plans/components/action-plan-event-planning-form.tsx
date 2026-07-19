import { ChevronRight, Plus, Trash2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { TerrainCard, TerrainSectionLabel, TerrainSwitch } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import type { ActionPlanRecurrenceDay } from '../lib/action-plan-schedule-constants'
import {
  createActionPlanAssigneeDraft,
  type ActionPlanAssigneeDraft,
} from '../lib/action-plan-form-validation'
import {
  buildScheduleRequestForAssignee,
  buildUseRequestForAssignee,
  combineDateAndTimeToIso,
  formatAssigneeSummary,
  hasGlobalRepeat,
  resolveNowStartForPlanning,
  snapTimeToFiveMinutes,
  splitIsoToDateAndTime,
  validateAssigneePlanningAction,
  type ActionPlanEventPlanningConfig,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import type { ActionPlanScheduleCreateRequest, ActionPlanUseRequest } from '../types'
import { ActionPlanAssigneesSheet } from './action-plan-assignees-sheet'
import { PlanningDateRow } from './planning/planning-date-row'
import {
  PlanningDateTimeRow,
  type PlanningPickerTarget,
} from './planning/planning-date-time-row'
import { RecurrenceDaysPicker } from './planning/recurrence-days-picker'

type ActionPlanEventPlanningFormProps = {
  draft: ActionPlanEventPlanningDraft
  config: ActionPlanEventPlanningConfig
  establishmentId: string
  pilotBusinessUnitId: string
  fieldErrors?: Record<string, string>
  onDraftChange: (draft: ActionPlanEventPlanningDraft) => void
  onAssigneeSchedule?: (assigneeId: string, body: ActionPlanScheduleCreateRequest) => void
  onAssigneeLaunch?: (assigneeId: string, body: ActionPlanUseRequest) => void
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

function assigneeFieldError(
  fieldErrors: Record<string, string>,
  assigneeId: string,
  field: string,
): string | undefined {
  return fieldErrors[`assignee.${assigneeId}.${field}`]
}

export function ActionPlanEventPlanningForm({
  draft,
  config,
  establishmentId,
  pilotBusinessUnitId,
  fieldErrors = {},
  onDraftChange,
  onAssigneeSchedule,
  onAssigneeLaunch,
}: ActionPlanEventPlanningFormProps) {
  const showNowAction = config.planningPersisted !== false
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)
  const [openPicker, setOpenPicker] = useState<PlanningPickerTarget>(null)
  const [assigneeActionErrors, setAssigneeActionErrors] = useState<Record<string, string>>({})

  function updateDraft(patch: Partial<ActionPlanEventPlanningDraft>) {
    onDraftChange({ ...draft, ...patch })
  }

  function updateAssignee(id: string, patch: Partial<ActionPlanAssigneeDraft>) {
    updateDraft({
      assignees: draft.assignees.map((assignee) =>
        assignee.id === id ? { ...assignee, ...patch } : assignee,
      ),
    })
  }

  function renderNowButton(apply: (parts: { date: string; time: string }) => void) {
    if (!showNowAction) {
      return undefined
    }
    return (
      <Button
        type="button"
        variant="outline"
        size="xs"
        className="h-7 rounded-full border-[#E8E6DF] bg-white px-2.5 text-xs font-medium text-[#114660]"
        onClick={() => apply(resolveNowStartForPlanning())}
      >
        Maintenant
      </Button>
    )
  }

  function handleGlobalRepeatToggle(repeatEnabled: boolean) {
    updateDraft({ repeatEnabled })
  }

  function handleStartDateChange(startDate: string) {
    updateDraft({ startDate })
  }

  function handleAssigneeSchedule(assignee: ActionPlanAssigneeDraft) {
    const errors = validateAssigneePlanningAction(draft, assignee.id, {
      allowRepeat: config.canSchedule,
      action: 'schedule',
    })
    setAssigneeActionErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }
    const body = buildScheduleRequestForAssignee(draft, assignee, {
      staffMode: config.staffMode,
    })
    if (!body || !onAssigneeSchedule) {
      return
    }
    onAssigneeSchedule(assignee.id, body)
  }

  function handleAssigneeLaunch(assignee: ActionPlanAssigneeDraft) {
    const errors = validateAssigneePlanningAction(draft, assignee.id, { action: 'launch' })
    setAssigneeActionErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }
    const body = buildUseRequestForAssignee(draft, assignee)
    if (!body || !onAssigneeLaunch) {
      return
    }
    onAssigneeLaunch(assignee.id, body)
  }

  const assigneeSummary = formatAssigneeSummary(draft.assignees, {
    staffMode: config.staffMode,
    staffDisplayName: config.staffDisplayName,
  })

  const showAssignees = !config.hideAssignees
  const showGlobalPlanning = !draft.usePerAssigneeChronology
  const showAssigneePlanning =
    draft.usePerAssigneeChronology &&
    (config.showAdvancedChronology || config.lockChronologyMode === true)
  const canToggleRepeat = config.canSchedule && showGlobalPlanning
  const canToggleChronology =
    config.showAdvancedChronology && config.lockChronologyMode !== true
  const lockStart = config.lockStart === true
  const assigneeActionsEnabled = config.assigneeActionsEnabled !== false
  const mergedFieldErrors = { ...fieldErrors, ...assigneeActionErrors }
  const chronologyModeLabel = draft.usePerAssigneeChronology
    ? 'Chronologie par assigné'
    : 'Chronologie commune'

  return (
    <>
      <section className="space-y-2">
        <TerrainSectionLabel>Planification</TerrainSectionLabel>
        <p className="px-0.5 text-xs text-[#7D7B75]">{chronologyModeLabel}</p>
        {config.planningPersisted === false ? (
          <p className="text-xs text-[#7D7B75]">
            La planification n&apos;est pas enregistrée avec le template.
          </p>
        ) : null}
        <TerrainCard className="overflow-hidden p-0">
          {showAssignees ? (
            <PlanningFormRow
              label="Assignés"
              summary={assigneeSummary}
              onClick={
                config.canEditAssignees ? () => setAssigneeSheetOpen(true) : undefined
              }
              disabled={!config.canEditAssignees}
              error={mergedFieldErrors.assignees}
            />
          ) : null}

          {canToggleChronology ? (
            <TerrainSwitch
              variant="bordered"
              label="Chronologie par assigné"
              checked={draft.usePerAssigneeChronology}
              onCheckedChange={(usePerAssigneeChronology) =>
                updateDraft({
                  usePerAssigneeChronology,
                  repeatEnabled: usePerAssigneeChronology ? false : draft.repeatEnabled,
                })
              }
            />
          ) : null}

          {canToggleRepeat ? (
            <TerrainSwitch
              variant="bordered"
              label="Répéter"
              checked={draft.repeatEnabled}
              onCheckedChange={handleGlobalRepeatToggle}
            />
          ) : null}

          {showAssigneePlanning ? (
            <div className="space-y-3 border-b border-[#E8E6DF] px-3 pt-3 pb-3">
              {draft.assignees.map((assignee) => {
                const startParts = splitIsoToDateAndTime(assignee.startAt)
                const endParts = splitIsoToDateAndTime(assignee.endAt)
                const showAssigneeRepeat = config.canSchedule && assignee.repeatEnabled
                return (
                  <div
                    key={assignee.id}
                    className="overflow-hidden rounded-xl border border-[#E8E6DF]"
                  >
                    <div className="flex items-center justify-between gap-2 border-b border-[#E8E6DF] px-3 py-2">
                      <p className="text-sm font-medium text-[#1a1a1a]">
                        {assignee.displayName || 'Assigné'}
                      </p>
                      {config.canEditAssignees ? (
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
                      ) : null}
                    </div>

                    {config.canSchedule ? (
                      <TerrainSwitch
                        variant="bordered"
                        label="Répéter"
                        checked={assignee.repeatEnabled}
                        onCheckedChange={(repeatEnabled) =>
                          updateAssignee(assignee.id, { repeatEnabled })
                        }
                      />
                    ) : null}

                    {showAssigneeRepeat ? (
                      <>
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-recurrence-start`}
                          label="Début de la récurrence"
                          date={startParts.date}
                          time={startParts.time}
                          hideTime
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
                          onTimeChange={() => undefined}
                          labelAddon={renderNowButton((parts) =>
                            updateAssignee(assignee.id, {
                              startAt: combineDateAndTimeToIso(parts.date, parts.time, 'start'),
                            }),
                          )}
                          error={assigneeFieldError(mergedFieldErrors, assignee.id, 'startDate')}
                        />
                        <PlanningDateRow
                          rowId={`assignee-${assignee.id}-recurrence-end`}
                          label="Fin de la récurrence"
                          date={assignee.recurrenceEndDate}
                          openPicker={openPicker}
                          onOpenPickerChange={setOpenPicker}
                          onDateChange={(recurrenceEndDate) =>
                            updateAssignee(assignee.id, { recurrenceEndDate })
                          }
                          error={assigneeFieldError(
                            mergedFieldErrors,
                            assignee.id,
                            'recurrenceEndDate',
                          )}
                        />
                        <div className="border-b border-[#E8E6DF] last:border-b-0">
                          <div className="flex items-center justify-between gap-3 px-3 py-3">
                            <span className="text-sm text-[#1a1a1a]">Jours</span>
                          </div>
                          <div className="space-y-2 px-3 pb-3">
                            <RecurrenceDaysPicker
                              value={assignee.recurrenceDays}
                              onChange={(recurrenceDays: ActionPlanRecurrenceDay[]) =>
                                updateAssignee(assignee.id, { recurrenceDays })
                              }
                              error={assigneeFieldError(
                                mergedFieldErrors,
                                assignee.id,
                                'recurrenceDays',
                              )}
                            />
                          </div>
                        </div>
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-slot-start`}
                          label="Début du créneau d'exécution"
                          date={startParts.date}
                          time={startParts.time}
                          hideDate
                          openPicker={openPicker}
                          onOpenPickerChange={setOpenPicker}
                          onDateChange={() => undefined}
                          onTimeChange={(time) =>
                            updateAssignee(assignee.id, {
                              startAt: combineDateAndTimeToIso(
                                startParts.date,
                                snapTimeToFiveMinutes(time),
                                'start',
                              ),
                            })
                          }
                          error={assigneeFieldError(mergedFieldErrors, assignee.id, 'startTime')}
                        />
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-slot-end`}
                          label="Fin du créneau d'exécution"
                          date={startParts.date}
                          time={endParts.time}
                          hideDate
                          openPicker={openPicker}
                          onOpenPickerChange={setOpenPicker}
                          onDateChange={() => undefined}
                          onTimeChange={(time) =>
                            updateAssignee(assignee.id, {
                              endAt: combineDateAndTimeToIso(
                                startParts.date,
                                snapTimeToFiveMinutes(time),
                                'end',
                              ),
                            })
                          }
                          error={assigneeFieldError(mergedFieldErrors, assignee.id, 'endTime')}
                        />
                      </>
                    ) : (
                      <>
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-start`}
                          label="Début"
                          date={startParts.date}
                          time={startParts.time}
                          disabled={lockStart}
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
                          labelAddon={renderNowButton((parts) =>
                            updateAssignee(assignee.id, {
                              startAt: combineDateAndTimeToIso(parts.date, parts.time, 'start'),
                            }),
                          )}
                          error={
                            assigneeFieldError(mergedFieldErrors, assignee.id, 'startDate') ??
                            assigneeFieldError(mergedFieldErrors, assignee.id, 'startTime')
                          }
                        />
                        <PlanningDateTimeRow
                          rowId={`assignee-${assignee.id}-end`}
                          label="Fin"
                          date={endParts.date}
                          time={endParts.time}
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
                          error={
                            assigneeFieldError(mergedFieldErrors, assignee.id, 'endDate') ??
                            assigneeFieldError(mergedFieldErrors, assignee.id, 'endTime')
                          }
                        />
                      </>
                    )}

                    {assigneeActionsEnabled ? (
                      <div className="border-t border-[#E8E6DF] px-3 py-3">
                        <Button
                          type="button"
                          className="h-10 w-full rounded-xl"
                          disabled={Boolean(config.assigneeActionPending?.[assignee.id])}
                          onClick={() =>
                            assignee.repeatEnabled
                              ? handleAssigneeSchedule(assignee)
                              : handleAssigneeLaunch(assignee)
                          }
                        >
                          {assignee.repeatEnabled
                            ? 'Planifier la récurrence'
                            : 'Lancer pour cet assigné'}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                )
              })}
              {config.canEditAssignees ? (
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
              ) : null}
            </div>
          ) : null}

          {showGlobalPlanning ? (
            hasGlobalRepeat(draft) ? (
              <>
                <PlanningDateTimeRow
                  rowId="global-recurrence-start"
                  label="Début de la récurrence"
                  date={draft.startDate}
                  time={draft.startTime}
                  hideTime
                  openPicker={openPicker}
                  onOpenPickerChange={setOpenPicker}
                  onDateChange={handleStartDateChange}
                  onTimeChange={() => undefined}
                  labelAddon={renderNowButton((parts) =>
                    updateDraft({ startDate: parts.date, startTime: parts.time }),
                  )}
                  error={mergedFieldErrors.startDate}
                />
                <PlanningDateRow
                  rowId="global-recurrence-end"
                  label="Fin de la récurrence"
                  date={draft.recurrenceEndDate}
                  openPicker={openPicker}
                  onOpenPickerChange={setOpenPicker}
                  onDateChange={(recurrenceEndDate) => updateDraft({ recurrenceEndDate })}
                  error={mergedFieldErrors.recurrenceEndDate}
                />
                <div className="border-b border-[#E8E6DF] last:border-b-0">
                  <div className="flex items-center justify-between gap-3 px-3 py-3">
                    <span className="text-sm text-[#1a1a1a]">Jours</span>
                  </div>
                  <div className="space-y-2 px-3 pb-3">
                    <RecurrenceDaysPicker
                      value={draft.recurrenceDays}
                      onChange={(recurrenceDays: ActionPlanRecurrenceDay[]) =>
                        updateDraft({ recurrenceDays })
                      }
                      error={mergedFieldErrors.recurrenceDays}
                    />
                    {config.staffMode ? (
                      <p className="text-xs text-[#7D7B75]">
                        La planification récurrente vous sera assignée sur le pôle pilote du
                        modèle.
                      </p>
                    ) : null}
                  </div>
                </div>
                <PlanningDateTimeRow
                  rowId="global-slot-start"
                  label="Début du créneau d'exécution"
                  date={draft.startDate}
                  time={draft.startTime}
                  hideDate
                  openPicker={openPicker}
                  onOpenPickerChange={setOpenPicker}
                  onDateChange={() => undefined}
                  onTimeChange={(startTime) =>
                    updateDraft({ startTime: snapTimeToFiveMinutes(startTime) })
                  }
                  error={mergedFieldErrors.startTime}
                />
                <PlanningDateTimeRow
                  rowId="global-slot-end"
                  label="Fin du créneau d'exécution"
                  date={draft.startDate}
                  time={draft.endTime}
                  hideDate
                  openPicker={openPicker}
                  onOpenPickerChange={setOpenPicker}
                  onDateChange={() => undefined}
                  onTimeChange={(endTime) =>
                    updateDraft({ endTime: snapTimeToFiveMinutes(endTime) })
                  }
                  error={mergedFieldErrors.endTime}
                />
              </>
            ) : (
              <>
                <PlanningDateTimeRow
                  rowId="shared-start"
                  label="Début"
                  date={draft.startDate}
                  time={draft.startTime}
                  disabled={lockStart}
                  openPicker={openPicker}
                  onOpenPickerChange={setOpenPicker}
                  onDateChange={handleStartDateChange}
                  onTimeChange={(startTime) =>
                    updateDraft({ startTime: snapTimeToFiveMinutes(startTime) })
                  }
                  labelAddon={renderNowButton((parts) =>
                    updateDraft({ startDate: parts.date, startTime: parts.time }),
                  )}
                  error={
                    mergedFieldErrors.startAt ??
                    mergedFieldErrors.startTime ??
                    mergedFieldErrors.startDate
                  }
                />

                <PlanningDateTimeRow
                  rowId="shared-end"
                  label="Fin"
                  date={draft.endDate}
                  time={draft.endTime}
                  openPicker={openPicker}
                  onOpenPickerChange={setOpenPicker}
                  onDateChange={(endDate) => updateDraft({ endDate })}
                  onTimeChange={(endTime) =>
                    updateDraft({ endTime: snapTimeToFiveMinutes(endTime) })
                  }
                  error={
                    mergedFieldErrors.endDate ??
                    mergedFieldErrors.sharedEndAt ??
                    mergedFieldErrors.endAt ??
                    mergedFieldErrors.endTime
                  }
                />
              </>
            )
          ) : null}
        </TerrainCard>
      </section>

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
