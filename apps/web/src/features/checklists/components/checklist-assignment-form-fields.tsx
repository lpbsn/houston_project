import { Input } from '@/components/ui/input'
import { ActionCreateAssigneeSection } from '@/features/actions/components/action-create-assignee-section'
import type { ScopedUserSearchResult } from '@/features/actions/types'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  RECURRENCE_DAY_OPTIONS,
  toggleRecurrenceDay,
  type RecurrenceDay,
} from '@/features/checklists/lib/checklist-recurrence'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistAssignmentFormFieldsProps = {
  idPrefix: string
  establishmentId: string
  businessUnitId: string
  assignedTo: string
  selectedUser: ScopedUserSearchResult | null
  onAssignedToChange: (membershipId: string, user: ScopedUserSearchResult | null) => void
  startDate: string
  onStartDateChange: (value: string) => void
  endDate: string
  onEndDateChange: (value: string) => void
  startAt: string
  onStartAtChange: (value: string) => void
  endAt: string
  onEndAtChange: (value: string) => void
  recurrenceDays: string[]
  onRecurrenceDaysChange: (value: string[]) => void
  fieldErrors: Record<string, string>
  apiError?: string | null
  intro?: string
}

export function ChecklistAssignmentFormFields({
  idPrefix,
  establishmentId,
  businessUnitId,
  assignedTo,
  selectedUser,
  onAssignedToChange,
  startDate,
  onStartDateChange,
  endDate,
  onEndDateChange,
  startAt,
  onStartAtChange,
  endAt,
  onEndAtChange,
  recurrenceDays,
  onRecurrenceDaysChange,
  fieldErrors,
  apiError,
  intro,
}: ChecklistAssignmentFormFieldsProps) {
  return (
    <div className="space-y-3 pb-4">
      {intro ? <p className={cn('text-xs leading-5', terrain.muted)}>{intro}</p> : null}

      {apiError ? <ChecklistFeedback variant="error" message={apiError} /> : null}

      <ActionCreateAssigneeSection
        establishmentId={establishmentId}
        businessUnitId={businessUnitId}
        assignedTo={assignedTo}
        selectedUser={selectedUser}
        onAssignedToChange={onAssignedToChange}
      />

      {fieldErrors.assignedTo ? (
        <p className="text-xs text-destructive">{fieldErrors.assignedTo}</p>
      ) : null}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-[#7D7B75]"
            htmlFor={`${idPrefix}-start-date`}
          >
            Date de début
          </label>
          <Input
            id={`${idPrefix}-start-date`}
            type="date"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="h-10 border-[#E8E6DF] text-sm"
          />
          {fieldErrors.startDate ? (
            <p className="text-xs text-destructive">{fieldErrors.startDate}</p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-[#7D7B75]"
            htmlFor={`${idPrefix}-end-date`}
          >
            Date de fin
          </label>
          <Input
            id={`${idPrefix}-end-date`}
            type="date"
            value={endDate}
            onChange={(e) => onEndDateChange(e.target.value)}
            className="h-10 border-[#E8E6DF] text-sm"
          />
          {fieldErrors.endDate ? (
            <p className="text-xs text-destructive">{fieldErrors.endDate}</p>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-[#7D7B75]"
            htmlFor={`${idPrefix}-start-at`}
          >
            Heure de début
          </label>
          <Input
            id={`${idPrefix}-start-at`}
            type="time"
            value={startAt}
            onChange={(e) => onStartAtChange(e.target.value)}
            className="h-10 border-[#E8E6DF] text-sm"
          />
          {fieldErrors.startAt ? (
            <p className="text-xs text-destructive">{fieldErrors.startAt}</p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#7D7B75]" htmlFor={`${idPrefix}-end-at`}>
            Heure de fin
          </label>
          <Input
            id={`${idPrefix}-end-at`}
            type="time"
            value={endAt}
            onChange={(e) => onEndAtChange(e.target.value)}
            className="h-10 border-[#E8E6DF] text-sm"
          />
          {fieldErrors.endAt ? (
            <p className="text-xs text-destructive">{fieldErrors.endAt}</p>
          ) : null}
        </div>
      </div>

      <div className="space-y-1.5">
        <p className="text-xs font-medium text-[#7D7B75]">Récurrence (optionnel)</p>
        <p className={cn('text-[11px]', terrain.mutedLight)}>
          Laissez vide pour une exécution ponctuelle.
        </p>
        <div className="flex flex-wrap gap-2">
          {RECURRENCE_DAY_OPTIONS.map((option) => {
            const selected = recurrenceDays.includes(option.value)
            return (
              <button
                key={option.value}
                type="button"
                onClick={() =>
                  onRecurrenceDaysChange(
                    toggleRecurrenceDay(recurrenceDays, option.value as RecurrenceDay),
                  )
                }
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                  selected
                    ? 'bg-[#EEF2FF] text-[#1B4FD8]'
                    : 'bg-[#F0EFE9] text-[#7D7B75]',
                )}
              >
                {option.label}
              </button>
            )
          })}
        </div>
        {fieldErrors.recurrenceDays ? (
          <p className="text-xs text-destructive">{fieldErrors.recurrenceDays}</p>
        ) : null}
      </div>
    </div>
  )
}
