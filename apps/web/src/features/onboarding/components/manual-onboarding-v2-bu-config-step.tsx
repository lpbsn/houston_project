import { LoaderCircle, Plus, Search, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useActivitySubjectSuggestions } from '@/features/onboarding/hooks'
import {
  createDraftActivitySubject,
  getBusinessUnitTypeDisplayValue,
  isBusinessUnitConfigured,
  type BusinessUnitType,
  type DraftActivitySubject,
  type DraftBusinessUnit,
} from '@/features/onboarding/lib/manual-v2-proposal'

const BUSINESS_UNIT_DESCRIPTION_MAX_LENGTH = 500

type ManualOnboardingV2BuConfigStepProps = {
  activitySubjects: DraftActivitySubject[]
  businessUnits: DraftBusinessUnit[]
  disabled?: boolean
  isSeedingSubjects?: boolean
  onBusinessUnitDescriptionChange: (clientKey: string, description: string) => void
  onBusinessUnitTypeChange: (clientKey: string, unitType: BusinessUnitType) => void
  onChange: (activitySubjects: DraftActivitySubject[]) => void
  onExcludeCatalogSubject: (businessUnitClientKey: string, catalogKey: string) => void
}

function hasDuplicateSubjectLabel(
  activitySubjects: DraftActivitySubject[],
  businessUnitClientKey: string,
  label: string,
) {
  const normalized = label.trim().toLowerCase()
  return activitySubjects.some(
    (item) =>
      item.business_unit_client_key === businessUnitClientKey &&
      item.label.trim().toLowerCase() === normalized,
  )
}

function BusinessUnitTypeSelector({
  businessUnit,
  disabled,
  onBusinessUnitTypeChange,
}: {
  businessUnit: DraftBusinessUnit
  disabled?: boolean
  onBusinessUnitTypeChange: (clientKey: string, unitType: BusinessUnitType) => void
}) {
  const displayValue = getBusinessUnitTypeDisplayValue(businessUnit)

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">Type de pôle</p>
      <div className="flex flex-wrap gap-2">
        {(
          [
            { value: 'dedicated' as const, label: 'Dédié' },
            { value: 'transversal' as const, label: 'Transversal' },
          ] as const
        ).map((option) => {
          const isSelected = displayValue === option.value

          return (
            <Button
              key={option.value}
              type="button"
              variant={isSelected ? 'default' : 'outline'}
              disabled={disabled}
              onClick={() => onBusinessUnitTypeChange(businessUnit.client_key, option.value)}
              className={`h-10 rounded-[0.9rem] ${
                isSelected
                  ? ''
                  : 'border-[#e7dfd1] bg-white text-foreground hover:bg-[#fffaf2]'
              }`}
              aria-pressed={isSelected}
            >
              {option.label}
            </Button>
          )
        })}
      </div>
      {!businessUnit.unit_type_confirmed ? (
        <p className="text-xs text-muted-foreground">
          Suggestion catalogue :{' '}
          {businessUnit.suggested_unit_type === 'transversal' ? 'Transversal' : 'Dédié'}. Choisissez
          le type adapté à votre établissement.
        </p>
      ) : null}
    </div>
  )
}

function ActivitySubjectEditor({
  businessUnit,
  activitySubjects,
  disabled,
  onBusinessUnitDescriptionChange,
  onBusinessUnitTypeChange,
  onChange,
  onExcludeCatalogSubject,
}: {
  businessUnit: DraftBusinessUnit
  activitySubjects: DraftActivitySubject[]
  disabled?: boolean
  onBusinessUnitDescriptionChange: (clientKey: string, description: string) => void
  onBusinessUnitTypeChange: (clientKey: string, unitType: BusinessUnitType) => void
  onChange: (activitySubjects: DraftActivitySubject[]) => void
  onExcludeCatalogSubject: (businessUnitClientKey: string, catalogKey: string) => void
}) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedQuery(query.trim())
    }, 250)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [query])

  const suggestionsQuery = useActivitySubjectSuggestions(
    businessUnit.catalog_key ?? '',
    debouncedQuery,
    {
      enabled: Boolean(businessUnit.catalog_key) && debouncedQuery.length >= 2,
    },
  )

  const subjectsForUnit = useMemo(
    () =>
      activitySubjects.filter(
        (subject) => subject.business_unit_client_key === businessUnit.client_key,
      ),
    [activitySubjects, businessUnit.client_key],
  )

  function addSubject(draft: DraftActivitySubject) {
    if (
      hasDuplicateSubjectLabel(
        activitySubjects,
        businessUnit.client_key,
        draft.label,
      )
    ) {
      return
    }

    onChange([...activitySubjects, draft])
  }

  function removeSubject(clientKey: string) {
    const subject = activitySubjects.find((item) => item.client_key === clientKey)

    if (subject?.catalog_key) {
      onExcludeCatalogSubject(businessUnit.client_key, subject.catalog_key)
    }

    onChange(activitySubjects.filter((item) => item.client_key !== clientKey))
  }

  const trimmedQuery = query.trim()

  return (
    <div className="space-y-3 rounded-[1.25rem] border border-[#ece5da] bg-[#fffdf9] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="font-semibold">{businessUnit.label}</h4>
        {businessUnit.unit_type_confirmed &&
        isBusinessUnitConfigured(businessUnit, activitySubjects) ? (
          <Badge className="bg-emerald-600 text-white">Configuré</Badge>
        ) : (
          <Badge variant="outline">Configuration requise</Badge>
        )}
      </div>

      <BusinessUnitTypeSelector
        businessUnit={businessUnit}
        disabled={disabled}
        onBusinessUnitTypeChange={onBusinessUnitTypeChange}
      />

      <div className="space-y-2">
        <label
          className="text-sm font-medium"
          htmlFor={`bu-description-${businessUnit.client_key}`}
        >
          Description du pôle (optionnel)
        </label>
        <textarea
          id={`bu-description-${businessUnit.client_key}`}
          disabled={disabled}
          value={businessUnit.description}
          maxLength={BUSINESS_UNIT_DESCRIPTION_MAX_LENGTH}
          onChange={(event) => {
            onBusinessUnitDescriptionChange(businessUnit.client_key, event.target.value)
          }}
          placeholder="Décrivez ce que couvre ce pôle pour votre établissement."
          className="min-h-24 w-full rounded-[0.9rem] border border-[#e7dfd1] bg-white px-3 py-2 text-sm"
        />
        <p className="text-xs text-muted-foreground">
          {businessUnit.description.length}/{BUSINESS_UNIT_DESCRIPTION_MAX_LENGTH} caractères
        </p>
      </div>

      {subjectsForUnit.length > 0 ? (
        <ul className="space-y-2">
          {subjectsForUnit.map((subject) => (
            <li
              key={subject.client_key}
              className="flex items-center justify-between rounded-[0.9rem] border border-[#ece5da] bg-white px-3 py-2"
            >
              <span className="text-sm font-medium">{subject.label}</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={disabled}
                onClick={() => removeSubject(subject.client_key)}
                aria-label={`Retirer ${subject.label}`}
              >
                <Trash2 className="size-4" />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          Ajoutez au moins un sujet d&apos;activité pour ce pôle.
        </p>
      )}

      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          disabled={disabled}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Rechercher ou saisir un sujet…"
          className="h-10 rounded-[0.9rem] border-[#e7dfd1] bg-white pl-10"
        />
      </div>

      {suggestionsQuery.isFetching ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" />
          Recherche en cours…
        </div>
      ) : null}

      {businessUnit.catalog_key && debouncedQuery.length >= 2 && suggestionsQuery.data?.length ? (
        <ul className="space-y-2">
          {suggestionsQuery.data.map((suggestion) => (
            <li key={suggestion.key}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  addSubject(
                    createDraftActivitySubject({
                      label: suggestion.label,
                      business_unit_client_key: businessUnit.client_key,
                      catalog_key: suggestion.key,
                    }),
                  )
                  setQuery('')
                  setDebouncedQuery('')
                }}
                className="flex w-full items-center justify-between rounded-[0.9rem] border border-[#ece5da] bg-white px-3 py-2 text-left text-sm transition hover:border-[color:var(--primary)]"
              >
                <span>{suggestion.label}</span>
                <Plus className="size-4 text-[color:var(--primary)]" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {trimmedQuery.length > 0 ? (
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          onClick={() => {
            addSubject(
              createDraftActivitySubject({
                label: trimmedQuery,
                business_unit_client_key: businessUnit.client_key,
              }),
            )
            setQuery('')
            setDebouncedQuery('')
          }}
          className="h-10 w-full rounded-[0.9rem] border-[#e7dfd1] bg-white text-sm"
        >
          <Plus className="size-4" />
          Ajouter « {trimmedQuery} »
        </Button>
      ) : null}
    </div>
  )
}

export function ManualOnboardingV2BuConfigStep({
  activitySubjects,
  businessUnits,
  disabled = false,
  isSeedingSubjects = false,
  onBusinessUnitDescriptionChange,
  onBusinessUnitTypeChange,
  onChange,
  onExcludeCatalogSubject,
}: ManualOnboardingV2BuConfigStepProps) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold">Étape 2 — Vos pôles</h3>
        <p className="text-sm leading-6 text-muted-foreground">
          Pour chaque pôle, choisissez s&apos;il est dédié ou transversal, ajoutez au moins un sujet
          d&apos;activité, et complétez la description si besoin.
        </p>
      </div>

      {isSeedingSubjects ? (
        <div className="flex items-center gap-2 rounded-[1rem] border border-[#ece5da] bg-white px-4 py-3 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" />
          Suggestions catalogue en cours…
        </div>
      ) : null}

      <div className="space-y-4">
        {businessUnits.map((businessUnit) => (
          <ActivitySubjectEditor
            key={businessUnit.client_key}
            businessUnit={businessUnit}
            activitySubjects={activitySubjects}
            disabled={disabled}
            onBusinessUnitDescriptionChange={onBusinessUnitDescriptionChange}
            onBusinessUnitTypeChange={onBusinessUnitTypeChange}
            onChange={onChange}
            onExcludeCatalogSubject={onExcludeCatalogSubject}
          />
        ))}
      </div>
    </div>
  )
}
