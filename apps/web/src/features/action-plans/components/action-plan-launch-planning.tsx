import { ChevronRight } from 'lucide-react'
import { useState } from 'react'

import {
  TerrainCard,
  TerrainSegmentedControl,
  TerrainSwitch,
} from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import type { ActionPlanRecurrenceDay } from '../lib/action-plan-schedule-constants'
import {
  formatAssigneeSummary,
  isAllDayPlanningDraft,
  resolveNowStartForPlanning,
  snapTimeToFiveMinutes,
  type ActionPlanEventPlanningConfig,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { ActionPlanAssigneesSheet } from './action-plan-assignees-sheet'
import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import { PlanningDateRow } from './planning/planning-date-row'
import {
  PlanningDateTimeRow,
  type PlanningPickerTarget,
} from './planning/planning-date-time-row'
import { RecurrenceDaysPicker } from './planning/recurrence-days-picker'

export type ActionPlanLaunchTiming = 'now' | 'schedule'

type ActionPlanLaunchPlanningProps = {
  draft: ActionPlanEventPlanningDraft
  config: ActionPlanEventPlanningConfig
  establishmentId: string
  pilotBusinessUnitId: string
  fieldErrors?: Record<string, string>
  timing: ActionPlanLaunchTiming
  advancedOpen: boolean
  onTimingChange: (timing: ActionPlanLaunchTiming) => void
  onAdvancedOpenChange: (open: boolean) => void
  onDraftChange: (
    update:
      | ActionPlanEventPlanningDraft
      | ((previous: ActionPlanEventPlanningDraft) => ActionPlanEventPlanningDraft),
  ) => void
}

export function ActionPlanLaunchPlanning({
  draft,
  config,
  establishmentId,
  pilotBusinessUnitId,
  fieldErrors = {},
  timing,
  advancedOpen,
  onTimingChange,
  onAdvancedOpenChange,
  onDraftChange,
}: ActionPlanLaunchPlanningProps) {
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)
  const [openPicker, setOpenPicker] = useState<PlanningPickerTarget>(null)
  const chronologyOn = draft.usePerAssigneeChronology
  const showScheduleFields = timing === 'schedule' && !chronologyOn
  const showAdvanced =
    config.showAdvancedChronology && config.lockChronologyMode !== true
  const advancedVisible = advancedOpen || chronologyOn

  function updateDraft(patch: Partial<ActionPlanEventPlanningDraft>) {
    onDraftChange((previous) => ({ ...previous, ...patch }))
  }

  function handleAllDayToggle(allDay: boolean) {
    if (allDay) {
      const today = resolveNowStartForPlanning().date
      updateDraft({
        startDate: draft.startDate || today,
        endDate: draft.endDate || draft.startDate || today,
        startTime: '',
        endTime: '',
      })
      return
    }
    const now = resolveNowStartForPlanning()
    updateDraft({
      startTime: now.time,
      endTime: snapTimeToFiveMinutes(
        `${String((Number.parseInt(now.time.slice(0, 2), 10) + 1) % 24).padStart(2, '0')}:${now.time.slice(3, 5)}`,
      ),
    })
  }

  const assigneeSummary = formatAssigneeSummary(draft.assignees, {
    staffMode: config.staffMode,
    staffDisplayName: config.staffDisplayName,
  })

  return (
    <div className="space-y-3">
      {chronologyOn ? null : (
        <TerrainCard className="p-0">
          {config.hideAssignees ? null : (
            <div
              className="border-b border-[#E8E6DF]"
              data-action-plan-field="assignees"
            >
              {config.canEditAssignees ? (
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left active:bg-[#F5F4F0]"
                  onClick={() => setAssigneeSheetOpen(true)}
                >
                  <span className="text-sm text-[#1a1a1a]">Assignés</span>
                  <span className="flex min-w-0 items-center gap-1.5 text-sm text-[#7D7B75]">
                    <span className="truncate">{assigneeSummary}</span>
                    <ChevronRight className="size-4 shrink-0" aria-hidden />
                  </span>
                </button>
              ) : (
                <div className="flex items-center justify-between gap-3 px-3 py-3">
                  <span className="text-sm text-[#1a1a1a]">Assignés</span>
                  <span className="truncate text-sm text-[#7D7B75]">{assigneeSummary}</span>
                </div>
              )}
              {fieldErrors.assignees ? (
                <p className="px-3 pb-2 text-xs text-destructive">{fieldErrors.assignees}</p>
              ) : null}
            </div>
          )}
          <div className="px-3 py-3">
            <TerrainSegmentedControl
              ariaLabel="Quand"
              value={timing}
              options={[
                { value: 'now', label: 'Maintenant' },
                { value: 'schedule', label: 'Planifier' },
              ]}
              onChange={onTimingChange}
            />
          </div>
          {showScheduleFields ? (
            <>
              <TerrainSwitch
                variant="bordered"
                label="Journée entière"
                checked={isAllDayPlanningDraft(draft)}
                onCheckedChange={handleAllDayToggle}
              />
              {config.canSchedule ? (
                <TerrainSwitch
                  variant="bordered"
                  label="Répéter"
                  checked={draft.repeatEnabled}
                  onCheckedChange={(repeatEnabled) => updateDraft({ repeatEnabled })}
                />
              ) : null}
              {draft.repeatEnabled && config.canSchedule ? (
                <>
                  <PlanningDateTimeRow
                    rowId="launch-repeat-start"
                    label="Début"
                    date={draft.startDate}
                    time={draft.startTime}
                    hideTime
                    disabled={config.lockStart === true}
                    openPicker={openPicker}
                    onOpenPickerChange={setOpenPicker}
                    onDateChange={(startDate) => updateDraft({ startDate })}
                    onTimeChange={() => undefined}
                    error={fieldErrors.startDate}
                    fieldKey="startDate"
                  />
                  <PlanningDateRow
                    rowId="launch-recurrence-end"
                    label="Fin de la récurrence"
                    date={draft.recurrenceEndDate}
                    openPicker={openPicker}
                    onOpenPickerChange={setOpenPicker}
                    onDateChange={(recurrenceEndDate) => updateDraft({ recurrenceEndDate })}
                    error={fieldErrors.recurrenceEndDate}
                    fieldKey="recurrenceEndDate"
                  />
                  <div className="border-b border-[#E8E6DF] last:border-b-0">
                    <div className="px-3 py-3 text-sm text-[#1a1a1a]">Jours</div>
                    <div className="space-y-2 px-3 pb-3">
                      <RecurrenceDaysPicker
                        value={draft.recurrenceDays}
                        onChange={(recurrenceDays: ActionPlanRecurrenceDay[]) =>
                          updateDraft({ recurrenceDays })
                        }
                        error={fieldErrors.recurrenceDays}
                        fieldKey="recurrenceDays"
                      />
                    </div>
                  </div>
                  {isAllDayPlanningDraft(draft) ? null : (
                    <>
                      <PlanningDateTimeRow
                        rowId="launch-slot-start"
                        label="Début du créneau"
                        date={draft.startDate}
                        time={draft.startTime}
                        hideDate
                        openPicker={openPicker}
                        onOpenPickerChange={setOpenPicker}
                        onDateChange={() => undefined}
                        onTimeChange={(startTime) =>
                          updateDraft({ startTime: snapTimeToFiveMinutes(startTime) })
                        }
                        error={fieldErrors.startTime}
                        fieldKey="startTime"
                      />
                      <PlanningDateTimeRow
                        rowId="launch-slot-end"
                        label="Fin du créneau"
                        date={draft.startDate}
                        time={draft.endTime}
                        hideDate
                        openPicker={openPicker}
                        onOpenPickerChange={setOpenPicker}
                        onDateChange={() => undefined}
                        onTimeChange={(endTime) =>
                          updateDraft({ endTime: snapTimeToFiveMinutes(endTime) })
                        }
                        error={fieldErrors.endTime}
                        fieldKey="endTime"
                      />
                    </>
                  )}
                </>
              ) : (
                <>
                  <PlanningDateTimeRow
                    rowId="launch-start"
                    label="Début"
                    date={draft.startDate}
                    time={draft.startTime}
                    disabled={config.lockStart === true}
                    hideTime={isAllDayPlanningDraft(draft)}
                    openPicker={openPicker}
                    onOpenPickerChange={setOpenPicker}
                    onDateChange={(startDate) => updateDraft({ startDate })}
                    onTimeChange={(startTime) =>
                      updateDraft({ startTime: snapTimeToFiveMinutes(startTime) })
                    }
                    error={fieldErrors.startDate ?? fieldErrors.startTime}
                    fieldKey={fieldErrors.startTime ? 'startTime' : 'startDate'}
                  />
                  <PlanningDateTimeRow
                    rowId="launch-end"
                    label="Fin"
                    date={draft.endDate}
                    time={draft.endTime}
                    hideTime={isAllDayPlanningDraft(draft)}
                    openPicker={openPicker}
                    onOpenPickerChange={setOpenPicker}
                    onDateChange={(endDate) => updateDraft({ endDate })}
                    onTimeChange={(endTime) =>
                      updateDraft({ endTime: snapTimeToFiveMinutes(endTime) })
                    }
                    error={fieldErrors.endDate ?? fieldErrors.endTime}
                    fieldKey={fieldErrors.endDate ? 'endDate' : 'endTime'}
                  />
                </>
              )}
            </>
          ) : null}
        </TerrainCard>
      )}

      {showAdvanced ? (
        <section className="space-y-2">
          <button
            type="button"
            className="flex w-full items-center justify-between px-1 py-1 text-left text-sm font-medium text-[#1a1a1a]"
            aria-expanded={advancedVisible}
            onClick={() => onAdvancedOpenChange(!advancedOpen)}
          >
            Options avancées
            <ChevronRight
              className={cn('size-4 text-[#7D7B75] transition-transform', advancedVisible && 'rotate-90')}
              aria-hidden
            />
          </button>
          {advancedVisible && !chronologyOn ? (
            <TerrainCard className="p-0">
              <TerrainSwitch
                variant="bordered"
                label="Chronologie par assigné"
                checked={false}
                onCheckedChange={(checked) => {
                  if (!checked) {
                    return
                  }
                  updateDraft({
                    usePerAssigneeChronology: true,
                    repeatEnabled: false,
                  })
                }}
              />
            </TerrainCard>
          ) : null}
          {chronologyOn ? (
            <ActionPlanEventPlanningForm
              draft={draft}
              config={{ ...config, assigneeActionsEnabled: false }}
              establishmentId={establishmentId}
              pilotBusinessUnitId={pilotBusinessUnitId}
              fieldErrors={fieldErrors}
              onDraftChange={onDraftChange}
            />
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
    </div>
  )
}
