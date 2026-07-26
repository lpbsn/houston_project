import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { useQualifyRoutingOptionsQuery } from '../hooks'
import {
  applyAffectedSelection,
  applyIssueFocusChange,
  applyResponsibleSelection,
  applySubjectSelection,
  buildQualifyRoutingPatch,
  canSubmitQualifyRoutingForm,
  createQualifyFormState,
  listAffectedBusinessUnitOptions,
  listAllRoutableSubjectOptions,
  listResponsibleBusinessUnitOptions,
  listSubjectOptionsForResponsible,
  withBaselineQualifyOptions,
  type SignalQualifyFormState,
} from '../lib/signal-qualify-form'
import type { SignalDetail } from '../types'

type SignalQualifyRoutingSheetProps = {
  open: boolean
  establishmentId: string
  signal: SignalDetail
  isPending: boolean
  errorMessage?: string | null
  onClose: () => void
  onSubmit: (patch: ReturnType<typeof buildQualifyRoutingPatch>) => void
}

const NONE_VALUE = '__none__'

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  id: string
  label: string
  value: string | null
  options: Array<{ id: string; label: string }>
  onChange: (next: string | null) => void
  disabled?: boolean
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-[12px] font-medium text-[#7D7B75]">
        {label}
      </label>
      <select
        id={id}
        className="h-11 w-full rounded-xl border border-[#E8E6DF] bg-white px-3 text-[14px] text-[#1a1a1a]"
        value={value ?? NONE_VALUE}
        disabled={disabled}
        onChange={(event) => {
          const next = event.target.value
          onChange(next === NONE_VALUE ? null : next)
        }}
      >
        <option value={NONE_VALUE}>Non défini</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export function SignalQualifyRoutingSheet({
  open,
  establishmentId,
  signal,
  isPending,
  errorMessage,
  onClose,
  onSubmit,
}: SignalQualifyRoutingSheetProps) {
  const baseline = useMemo(() => createQualifyFormState(signal), [signal])
  const [draft, setDraft] = useState<SignalQualifyFormState>(() => baseline)
  const optionsQuery = useQualifyRoutingOptionsQuery(establishmentId, {
    staleTime: 60_000,
    enabled: open,
  })
  const businessUnits = useMemo(
    () => optionsQuery.data?.business_units ?? [],
    [optionsQuery.data?.business_units],
  )

  const catalogueAffected = useMemo(
    () => listAffectedBusinessUnitOptions(businessUnits),
    [businessUnits],
  )
  const catalogueResponsible = useMemo(
    () => listResponsibleBusinessUnitOptions(businessUnits),
    [businessUnits],
  )
  const allSubjects = useMemo(
    () => listAllRoutableSubjectOptions(businessUnits),
    [businessUnits],
  )
  const catalogueSubjects = useMemo(
    () => listSubjectOptionsForResponsible(businessUnits, draft.responsibleBusinessUnitId),
    [businessUnits, draft.responsibleBusinessUnitId],
  )

  const { affectedOptions, responsibleOptions, subjectOptions } = useMemo(
    () =>
      withBaselineQualifyOptions({
        affectedOptions: catalogueAffected,
        responsibleOptions: catalogueResponsible,
        subjectOptions: catalogueSubjects,
        baseline,
        draft,
        labels: {
          affectedBusinessUnitLabel: signal.affected_business_unit_label,
          responsibleBusinessUnitLabel: signal.responsible_business_unit_label,
          activitySubjectLabel: signal.activity_subject_label,
        },
      }),
    [
      catalogueAffected,
      catalogueResponsible,
      catalogueSubjects,
      baseline,
      draft,
      signal.affected_business_unit_label,
      signal.responsible_business_unit_label,
      signal.activity_subject_label,
    ],
  )

  const subjectsForDerivation = useMemo(() => {
    const orphan = subjectOptions.find(
      (item) => !allSubjects.some((subject) => subject.id === item.id),
    )
    return orphan ? [...allSubjects, orphan] : allSubjects
  }, [allSubjects, subjectOptions])

  const patch = buildQualifyRoutingPatch(baseline, draft)
  const canSubmit =
    canSubmitQualifyRoutingForm(baseline, draft) && !isPending && !optionsQuery.isLoading

  function handleSubjectChange(subjectId: string | null) {
    const subject = subjectsForDerivation.find((item) => item.id === subjectId) ?? null
    setDraft((current) =>
      applySubjectSelection(current, subjectId, subject?.businessUnitId ?? null),
    )
  }

  function handleResponsibleChange(responsibleId: string | null) {
    const currentSubject = subjectsForDerivation.find(
      (item) => item.id === draft.activitySubjectId,
    )
    setDraft((current) =>
      applyResponsibleSelection(
        current,
        responsibleId,
        currentSubject?.businessUnitId ?? null,
      ),
    )
  }

  return (
    <TerrainBottomSheet
      title="Qualifier le routage"
      open={open}
      onClose={onClose}
      footer={
        <Button
          type="button"
          className={cn(
            'h-11 w-full rounded-full text-[15px] font-semibold text-white',
            terrainBrandAction.bg,
            terrainBrandAction.hover,
          )}
          disabled={!canSubmit}
          onClick={() => onSubmit(patch)}
        >
          {isPending ? 'Enregistrement…' : 'Valider'}
        </Button>
      }
    >
      <div className="flex flex-col gap-3 pb-2">
        <p className="text-[13px] leading-snug text-[#7D7B75]">
          Choisissez un sujet pour dériver le pôle responsable, ou un responsable puis un sujet
          de ce pôle. Le pôle concerné reste indépendant.
        </p>

        <SelectField
          id="qualify-subject"
          label="Sujet"
          value={draft.activitySubjectId}
          options={subjectOptions}
          disabled={isPending || optionsQuery.isLoading}
          onChange={handleSubjectChange}
        />

        <SelectField
          id="qualify-responsible"
          label="Pôle responsable"
          value={draft.responsibleBusinessUnitId}
          options={responsibleOptions}
          disabled={isPending || optionsQuery.isLoading}
          onChange={handleResponsibleChange}
        />

        <SelectField
          id="qualify-affected"
          label="Pôle concerné"
          value={draft.affectedBusinessUnitId}
          options={affectedOptions}
          disabled={isPending || optionsQuery.isLoading}
          onChange={(next) => setDraft((current) => applyAffectedSelection(current, next))}
        />

        <div className="space-y-1.5">
          <label htmlFor="qualify-issue-focus" className="text-[12px] font-medium text-[#7D7B75]">
            Problème (issue focus)
          </label>
          <input
            id="qualify-issue-focus"
            type="text"
            maxLength={80}
            className="h-11 w-full rounded-xl border border-[#E8E6DF] bg-white px-3 text-[14px] text-[#1a1a1a]"
            value={draft.issueFocus}
            disabled={isPending}
            onChange={(event) =>
              setDraft((current) => applyIssueFocusChange(current, event.target.value))
            }
          />
        </div>

        {optionsQuery.isError ? (
          <p className="text-sm text-destructive" role="alert">
            Impossible de charger les pôles et sujets.
          </p>
        ) : null}
        {errorMessage ? (
          <p className="text-sm text-destructive" role="alert">
            {errorMessage}
          </p>
        ) : null}
      </div>
    </TerrainBottomSheet>
  )
}
