import { Building2, Check, Layers, Plus, Trash2, Users, X } from 'lucide-react'
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { bootstrapQueryKey, fetchBootstrap } from '@/features/auth/api'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  suggestActivitySubjects,
} from '@/features/onboarding/api'
import {
  useCatalogBusinessUnitChips,
  useCompleteOnboardingSession,
  useOnboardingDraft,
  useOnboardingDraftAutosave,
} from '@/features/onboarding/hooks'
import {
  addManualActivitySubject,
  applyCatalogBusinessUnitSelection,
  createEmptyBusinessUnit,
  removeActivitySubject,
} from '@/features/onboarding/lib/onboarding-draft-catalog'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import {
  ACTIVITY_DESCRIPTION_MAX_LENGTH,
  DRAFT_STEP_STRUCTURE,
  DRAFT_STEP_TEAM,
  OnboardingDraftPayloadParseError,
  parseOnboardingDraftPayload,
  stripEmptyMemberRows,
  withCurrentStep,
  type OnboardingDraftMember,
  type OnboardingDraftPayload,
  type OnboardingDraftPerson,
} from '@/features/onboarding/lib/onboarding-draft-payload'
import {
  canCompleteOnboardingDraft,
  canContinueFromStructureStep,
  removeBusinessUnitFromDraft,
  structureStickyMessage,
  subjectsForBusinessUnit,
} from '@/features/onboarding/lib/onboarding-draft-validation'
import {
  OnboardingErrorState,
  OnboardingLoadingState,
} from '@/features/onboarding/components/onboarding-state'

type DraftOnboardingWizardProps = {
  sessionId: string
  onNavigate?: (path: string) => void
}

function SaveStatus({ status }: { status: string }) {
  const label =
    status === 'saving'
      ? 'Enregistrement…'
      : status === 'saved'
        ? 'Enregistré'
        : status === 'error'
          ? 'Erreur d’enregistrement'
          : ''
  if (!label) return null
  return (
    <p
      className={`text-xs ${status === 'error' ? 'text-red-700' : 'text-spore-muted'}`}
      data-testid="onboarding-save-status"
    >
      {label}
    </p>
  )
}

function NewSubjectDialog({
  open,
  onClose,
  onAdd,
}: {
  open: boolean
  onClose: () => void
  onAdd: (input: { label: string; description: string }) => void
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const [label, setLabel] = useState('')
  const [description, setDescription] = useState('')

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open) {
      if (!dialog.open) dialog.showModal()
      setLabel('')
      setDescription('')
    } else if (dialog.open) {
      dialog.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="fixed inset-0 m-auto w-[min(100%,28rem)] rounded-2xl border-0 bg-white p-0 text-spore-forest shadow-2xl backdrop:bg-spore-forest/40 open:flex open:flex-col"
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose()
      }}
    >
      <div className="flex flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-spore-forest">
              Nouveau sujet
            </h2>
            <p className="mt-1 text-sm text-spore-muted">
              Renseignez le nom du sujet et une description optionnelle.
            </p>
          </div>
          <button
            type="button"
            aria-label="Fermer"
            className="rounded-lg p-1 text-spore-muted hover:bg-spore-cream"
            onClick={onClose}
          >
            <X className="size-4" />
          </button>
        </div>
        <label className="block space-y-1.5">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Nom du sujet
          </span>
          <Input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="Ex. Propreté, Accueil, Sécurité..."
            className="h-11 rounded-xl border-spore-forest/20"
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Description
          </span>
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Décrivez ce sujet (optionnel)..."
            className="min-h-24 rounded-xl border-spore-forest/15"
          />
        </label>
        <div className="flex items-center justify-between gap-3 pt-1">
          <button
            type="button"
            className="text-sm font-medium text-spore-muted hover:text-spore-forest"
            onClick={onClose}
          >
            Annuler
          </button>
          <Button
            type="button"
            disabled={label.trim().length === 0}
            className="h-10 rounded-xl bg-spore-moss text-white hover:bg-spore-forest"
            onClick={() => {
              onAdd({ label, description })
              onClose()
            }}
          >
            Ajouter le sujet
          </Button>
        </div>
      </div>
    </dialog>
  )
}

function StructureStep({
  draft,
  setDraft,
  catalogUnits,
  catalogLoading,
}: {
  draft: OnboardingDraftPayload
  setDraft: Dispatch<SetStateAction<OnboardingDraftPayload>>
  catalogUnits: Array<{ key: string; label: string; description: string; unit_type: string }>
  catalogLoading: boolean
}) {
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set())
  const [subjectModalBuKey, setSubjectModalBuKey] = useState<string | null>(null)
  const [seedingKey, setSeedingKey] = useState<string | null>(null)

  useEffect(() => {
    if (draft.business_units.length === 0) return
    setExpandedKeys((current) => {
      if (current.size > 0) return current
      return new Set([draft.business_units[0]!.client_key])
    })
  }, [draft.business_units])

  const unitTypeByKey = new Map(catalogUnits.map((unit) => [unit.key, unit.unit_type]))

  async function handleSelectCatalog(
    businessUnitClientKey: string,
    catalogUnit: { key: string; label: string; description: string; unit_type: string },
  ) {
    setSeedingKey(businessUnitClientKey)
    try {
      const subjects = await suggestActivitySubjects(catalogUnit.key, '', { limit: 200 })
      setDraft((current) =>
        applyCatalogBusinessUnitSelection(current, businessUnitClientKey, catalogUnit, subjects),
      )
    } finally {
      setSeedingKey(null)
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-spore-forest/10 bg-white p-5 sm:p-6">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-spore-forest text-white">
            <Building2 className="size-5" />
          </div>
          <h2 className="text-lg font-semibold text-spore-forest">Votre établissement</h2>
        </div>
        <div className="space-y-4">
          <label className="block space-y-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
              Nom de l’établissement
            </span>
            <Input
              value={draft.establishment.name}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  establishment: { ...current.establishment, name: event.target.value },
                }))
              }
              placeholder="Ex. Le Grand Hôtel Central"
              className="h-11 rounded-xl border-spore-forest/15"
            />
          </label>
          <label className="block space-y-1.5">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                Description
              </span>
              <span className="text-xs text-spore-muted">
                {draft.establishment.description.length} / {ACTIVITY_DESCRIPTION_MAX_LENGTH}
              </span>
            </div>
            <Textarea
              value={draft.establishment.description}
              maxLength={ACTIVITY_DESCRIPTION_MAX_LENGTH}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  establishment: { ...current.establishment, description: event.target.value },
                }))
              }
              placeholder="Décrivez votre établissement : type, capacité, spécificités, positionnement..."
              className="min-h-28 rounded-xl border-spore-forest/15"
            />
          </label>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-spore-forest">Pôles d’activité</h2>
            <p className="mt-1 text-sm text-spore-muted">
              Décrivez vos pôles et ajoutez leurs sujets de suivi.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            className="h-10 rounded-xl border-spore-forest/15 bg-white"
            onClick={() => {
              const unit = createEmptyBusinessUnit()
              setDraft((current) => ({
                ...current,
                business_units: [...current.business_units, unit],
              }))
              setExpandedKeys((current) => new Set([...current, unit.client_key]))
            }}
          >
            <Plus className="size-4" />
            Ajouter un pôle
          </Button>
        </div>

        {draft.business_units.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-spore-forest/20 bg-white/60 px-4 py-10 text-center text-sm text-spore-muted">
            Ajoutez un pôle pour commencer.
          </div>
        ) : null}

        {draft.business_units.map((unit, index) => {
          const expanded = expandedKeys.has(unit.client_key)
          const subjects = subjectsForBusinessUnit(draft, unit.client_key)
          const unitType = unit.catalog_key ? unitTypeByKey.get(unit.catalog_key) : null

          return (
            <article
              key={unit.client_key}
              className="overflow-hidden rounded-2xl border border-spore-forest/10 bg-white"
            >
              <header className="flex items-center gap-3 px-4 py-3 sm:px-5">
                <div className="flex size-9 items-center justify-center rounded-full bg-spore-moss/15 text-spore-forest">
                  <Layers className="size-4" />
                </div>
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() =>
                    setExpandedKeys((current) => {
                      const next = new Set(current)
                      if (next.has(unit.client_key)) next.delete(unit.client_key)
                      else next.add(unit.client_key)
                      return next
                    })
                  }
                >
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                    Pôle {index + 1}
                  </div>
                  <div className="truncate text-sm font-medium text-spore-forest">
                    {unit.specific_name.trim() || 'Sans nom'}
                    <span className="ml-2 font-normal text-spore-muted">
                      · {subjects.length} sujet{subjects.length === 1 ? '' : 's'}
                    </span>
                  </div>
                </button>
                <button
                  type="button"
                  aria-label="Supprimer le pôle"
                  className="rounded-lg p-2 text-spore-muted hover:bg-red-50 hover:text-red-700"
                  onClick={() =>
                    setDraft((current) => removeBusinessUnitFromDraft(current, unit.client_key))
                  }
                >
                  <Trash2 className="size-4" />
                </button>
              </header>

              {expanded ? (
                <div className="space-y-4 border-t border-spore-forest/8 px-4 py-4 sm:px-5">
                  <label className="block space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Nom du pôle
                    </span>
                    <Input
                      value={unit.specific_name}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          business_units: current.business_units.map((item) =>
                            item.client_key === unit.client_key
                              ? { ...item, specific_name: event.target.value }
                              : item,
                          ),
                        }))
                      }
                      placeholder="Ex. Hôtel, Restaurant, Coworking..."
                      className="h-11 rounded-xl border-spore-forest/15"
                    />
                  </label>

                  <div className="space-y-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Pôles disponibles
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {catalogLoading ? (
                        <span className="text-sm text-spore-muted">Chargement du catalogue…</span>
                      ) : (
                        catalogUnits.map((chip) => {
                          const selected = unit.catalog_key === chip.key
                          return (
                            <button
                              key={chip.key}
                              type="button"
                              disabled={seedingKey === unit.client_key}
                              onClick={() => void handleSelectCatalog(unit.client_key, chip)}
                              className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-sm transition ${
                                selected
                                  ? 'border-spore-moss bg-spore-moss/15 text-spore-forest'
                                  : 'border-spore-forest/15 bg-spore-cream/80 text-spore-forest hover:border-spore-moss'
                              }`}
                            >
                              <Plus className="size-3.5" />
                              {chip.label}
                            </button>
                          )
                        })
                      )}
                    </div>
                    {unitType ? (
                      <p className="text-xs text-spore-muted">
                        Type catalogue :{' '}
                        <span className="font-medium text-spore-forest">
                          {unitType === 'transversal' ? 'Pôle transversal' : 'Pôle dédié'}
                        </span>
                      </p>
                    ) : null}
                  </div>

                  <label className="block space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Description
                    </span>
                    <Textarea
                      value={unit.instance_description}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          business_units: current.business_units.map((item) =>
                            item.client_key === unit.client_key
                              ? { ...item, instance_description: event.target.value }
                              : item,
                          ),
                        }))
                      }
                      placeholder="Résumé court du périmètre de ce pôle..."
                      className="min-h-20 rounded-xl border-spore-forest/15"
                    />
                  </label>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                        Sujets ({subjects.length})
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        className="h-9 rounded-xl border-spore-forest/15"
                        onClick={() => setSubjectModalBuKey(unit.client_key)}
                      >
                        <Plus className="size-4" />
                        Ajouter un sujet
                      </Button>
                    </div>
                    {subjects.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-spore-forest/20 px-4 py-6 text-center text-sm text-spore-muted">
                        Aucun sujet. Sélectionnez un pôle du catalogue pour préremplir ses sujets,
                        ou ajoutez-en un.
                      </div>
                    ) : (
                      <ul className="space-y-2">
                        {subjects.map((subject) => (
                          <li
                            key={subject.client_key}
                            className="flex items-start justify-between gap-3 rounded-xl border border-spore-forest/10 px-3 py-2.5"
                          >
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium text-spore-forest">
                                {subject.label || subject.catalog_key}
                              </div>
                              {subject.description ? (
                                <p className="mt-0.5 text-xs text-spore-muted">{subject.description}</p>
                              ) : null}
                            </div>
                            <button
                              type="button"
                              aria-label="Supprimer le sujet"
                              className="rounded-lg p-1.5 text-spore-muted hover:bg-red-50 hover:text-red-700"
                              onClick={() =>
                                setDraft((current) =>
                                  removeActivitySubject(current, subject.client_key),
                                )
                              }
                            >
                              <Trash2 className="size-4" />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              ) : null}
            </article>
          )
        })}
      </section>

      <NewSubjectDialog
        open={subjectModalBuKey !== null}
        onClose={() => setSubjectModalBuKey(null)}
        onAdd={({ label, description }) => {
          if (!subjectModalBuKey) return
          setDraft((current) =>
            addManualActivitySubject(current, subjectModalBuKey, { label, description }),
          )
        }}
      />
    </div>
  )
}

function emptyDirector(): OnboardingDraftPerson {
  return { email: '', first_name: '', last_name: '' }
}

function emptyMember(): OnboardingDraftMember {
  return {
    email: '',
    first_name: '',
    last_name: '',
    role: 'manager',
    business_unit_client_keys: [],
  }
}

function TeamStepView({
  draft,
  setDraft,
}: {
  draft: OnboardingDraftPayload
  setDraft: Dispatch<SetStateAction<OnboardingDraftPayload>>
}) {
  const director = draft.team.director ?? emptyDirector()
  const poles = draft.business_units.filter((unit) => unit.specific_name.trim().length > 0)

  function updateDirector(patch: Partial<OnboardingDraftPerson>) {
    setDraft((current) => ({
      ...current,
      team: {
        ...current.team,
        director: { ...(current.team.director ?? emptyDirector()), ...patch },
      },
    }))
  }

  function updateMember(index: number, patch: Partial<OnboardingDraftMember>) {
    setDraft((current) => ({
      ...current,
      team: {
        ...current.team,
        members: current.team.members.map((member, memberIndex) =>
          memberIndex === index ? { ...member, ...patch } : member,
        ),
      },
    }))
  }

  return (
    <section className="rounded-2xl border border-spore-forest/10 bg-white p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-spore-forest text-white">
            <Users className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-spore-forest">Invitez votre équipe</h2>
            <p className="mt-1 text-sm text-spore-muted">
              Assignez chaque membre aux pôles d’activité qui le concernent.
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          className="h-10 rounded-xl border-spore-forest/15 bg-white"
          onClick={() =>
            setDraft((current) => ({
              ...current,
              team: { ...current.team, members: [...current.team.members, emptyMember()] },
            }))
          }
        >
          <Plus className="size-4" />
          Ajouter un membre
        </Button>
      </div>

      <div className="space-y-4">
        <div className="rounded-xl border border-spore-forest/10 p-4">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Directeur (obligatoire)
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="space-y-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                Prénom
              </span>
              <Input
                value={director.first_name}
                onChange={(event) => updateDirector({ first_name: event.target.value })}
                placeholder="Prénom"
                className="h-11 rounded-xl"
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                Nom
              </span>
              <Input
                value={director.last_name}
                onChange={(event) => updateDirector({ last_name: event.target.value })}
                placeholder="Nom"
                className="h-11 rounded-xl"
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                Email
              </span>
              <Input
                type="email"
                value={director.email}
                onChange={(event) => updateDirector({ email: event.target.value })}
                placeholder="nom@etablissement.fr"
                className="h-11 rounded-xl"
              />
            </label>
          </div>
          <p className="mt-3 text-xs text-spore-muted">Rôle : Directeur (non modifiable)</p>
        </div>

        {draft.team.members.length === 0 ? (
          <div className="rounded-xl border border-dashed border-spore-forest/20 px-4 py-10 text-center">
            <p className="font-medium text-spore-forest">Aucun membre</p>
            <p className="mt-1 text-sm text-spore-muted">
              Optionnel — vous pouvez terminer sans inviter personne
            </p>
            <Button
              type="button"
              className="mt-4 h-11 rounded-xl bg-spore-forest text-white hover:bg-spore-moss"
              onClick={() =>
                setDraft((current) => ({
                  ...current,
                  team: { ...current.team, members: [emptyMember()] },
                }))
              }
            >
              <Plus className="size-4" />
              Ajouter le premier membre
            </Button>
          </div>
        ) : (
          draft.team.members.map((member, index) => {
            const noPole = member.business_unit_client_keys.length === 0
            return (
              <div key={index} className="rounded-xl border border-spore-forest/10 p-4">
                <div className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_10rem_auto]">
                  <label className="space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Prénom
                    </span>
                    <Input
                      value={member.first_name}
                      onChange={(event) => updateMember(index, { first_name: event.target.value })}
                      placeholder="Prénom"
                      className="h-11 rounded-xl"
                    />
                  </label>
                  <label className="space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Nom
                    </span>
                    <Input
                      value={member.last_name}
                      onChange={(event) => updateMember(index, { last_name: event.target.value })}
                      placeholder="Nom"
                      className="h-11 rounded-xl"
                    />
                  </label>
                  <label className="space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Email
                    </span>
                    <Input
                      type="email"
                      value={member.email}
                      onChange={(event) => updateMember(index, { email: event.target.value })}
                      placeholder="nom@etablissement.fr"
                      className="h-11 rounded-xl"
                    />
                  </label>
                  <label className="space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                      Rôle
                    </span>
                    <select
                      value={member.role}
                      onChange={(event) =>
                        updateMember(index, {
                          role: event.target.value === 'staff' ? 'staff' : 'manager',
                        })
                      }
                      className="h-11 w-full rounded-xl border border-spore-forest/15 bg-white px-3 text-sm"
                    >
                      <option value="manager">Manager</option>
                      <option value="staff">Staff</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    aria-label="Supprimer le membre"
                    className="mt-6 rounded-lg p-2 text-spore-muted hover:bg-red-50 hover:text-red-700"
                    onClick={() =>
                      setDraft((current) => ({
                        ...current,
                        team: {
                          ...current.team,
                          members: current.team.members.filter((_, i) => i !== index),
                        },
                      }))
                    }
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>

                <div className="mt-4 space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
                    Pôles d’activité
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {poles.map((pole) => {
                      const selected = member.business_unit_client_keys.includes(pole.client_key)
                      return (
                        <button
                          key={pole.client_key}
                          type="button"
                          onClick={() => {
                            const keys = selected
                              ? member.business_unit_client_keys.filter(
                                  (key) => key !== pole.client_key,
                                )
                              : [...member.business_unit_client_keys, pole.client_key]
                            updateMember(index, { business_unit_client_keys: keys })
                          }}
                          className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-sm ${
                            selected
                              ? 'border-spore-moss bg-spore-moss/15 text-spore-forest'
                              : 'border-spore-forest/15 bg-spore-cream text-spore-forest'
                          }`}
                        >
                          {selected ? <Check className="size-3.5" /> : null}
                          {pole.specific_name}
                        </button>
                      )
                    })}
                  </div>
                  {noPole ? (
                    <span className="inline-flex rounded-full bg-orange-50 px-3 py-1 text-xs font-medium text-orange-700">
                      Aucun pôle assigné
                    </span>
                  ) : null}
                </div>
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}

export function DraftOnboardingWizard({ sessionId, onNavigate }: DraftOnboardingWizardProps) {
  const queryClient = useQueryClient()
  const draftQuery = useOnboardingDraft(sessionId)
  const catalogQuery = useCatalogBusinessUnitChips()
  const completeMutation = useCompleteOnboardingSession(sessionId)

  const [draft, setDraft] = useState<OnboardingDraftPayload | null>(null)
  const [hydrateError, setHydrateError] = useState<Error | null>(null)
  const [step, setStep] = useState<'structure' | 'team'>('structure')
  const [navError, setNavError] = useState<string | null>(null)
  const [isNavigating, setIsNavigating] = useState(false)
  const hydratedSessionRef = useRef<string | null>(null)

  const autosave = useOnboardingDraftAutosave({ sessionId })
  const { enqueue, flush, stop, resume, status: saveStatus } = autosave
  const skipNextEnqueueRef = useRef(false)

  useEffect(() => {
    hydratedSessionRef.current = null
    setDraft(null)
    setHydrateError(null)
    resume()
  }, [sessionId, resume])

  useEffect(() => {
    if (!draftQuery.data) return
    if (hydratedSessionRef.current === sessionId) return

    try {
      const parsed = parseOnboardingDraftPayload(draftQuery.data.payload)
      skipNextEnqueueRef.current = true
      setDraft(parsed)
      setStep(parsed.current_step === DRAFT_STEP_TEAM ? 'team' : 'structure')
      setHydrateError(null)
      hydratedSessionRef.current = sessionId
    } catch (error) {
      setHydrateError(
        error instanceof OnboardingDraftPayloadParseError
          ? error
          : new OnboardingDraftPayloadParseError(),
      )
    }
  }, [draftQuery.data, sessionId])

  useEffect(() => {
    if (!draft || hydratedSessionRef.current !== sessionId) return
    if (skipNextEnqueueRef.current) {
      skipNextEnqueueRef.current = false
      return
    }
    enqueue(draft)
  }, [draft, enqueue, sessionId])

  const updateDraft = useCallback((updater: SetStateAction<OnboardingDraftPayload>) => {
    setDraft((current) => {
      if (!current) return current
      return typeof updater === 'function' ? updater(current) : updater
    })
  }, [])

  if (draftQuery.isPending && !draft) {
    return <OnboardingLoadingState label="Chargement du brouillon d’onboarding…" />
  }

  if (draftQuery.error && !draft) {
    return (
      <OnboardingErrorState
        error={draftQuery.error}
        fallback="Le brouillon d’onboarding n’a pas pu être chargé."
      />
    )
  }

  if (hydrateError) {
    return (
      <OnboardingErrorState
        error={hydrateError}
        fallback="Le brouillon d’onboarding est incompatible."
      />
    )
  }

  if (!draft) {
    return <OnboardingLoadingState label="Préparation du parcours d’onboarding…" />
  }

  const structureOk = canContinueFromStructureStep(draft).ok
  const completeOk = canCompleteOnboardingDraft(draft).ok
  const stickyMessage =
    step === 'structure'
      ? structureStickyMessage(draft)
      : completeOk
        ? 'Vous pouvez terminer la configuration.'
        : 'Renseignez le directeur pour terminer.'

  async function handleContinue() {
    if (!draft || !structureOk || isNavigating) return
    setIsNavigating(true)
    setNavError(null)
    const snapshot = withCurrentStep(draft, DRAFT_STEP_TEAM)
    setDraft(snapshot)
    try {
      await flush(snapshot)
      setStep('team')
    } catch (error) {
      setNavError(getCompleteErrorMessage(error, 'Impossible d’enregistrer avant de continuer.'))
    } finally {
      setIsNavigating(false)
    }
  }

  async function handleBack() {
    if (!draft || isNavigating) return
    setIsNavigating(true)
    setNavError(null)
    const snapshot = withCurrentStep(draft, DRAFT_STEP_STRUCTURE)
    setDraft(snapshot)
    try {
      await flush(snapshot)
      setStep('structure')
    } catch (error) {
      setNavError(getCompleteErrorMessage(error, 'Impossible d’enregistrer avant de revenir.'))
    } finally {
      setIsNavigating(false)
    }
  }

  async function handleComplete() {
    if (!draft || !completeOk || completeMutation.isPending) return
    setNavError(null)
    const finalSnapshot = stripEmptyMemberRows(withCurrentStep(draft, DRAFT_STEP_TEAM))
    setDraft(finalSnapshot)
    stop()
    try {
      await flush(finalSnapshot)
      await completeMutation.mutateAsync()
      const bootstrap = await queryClient.fetchQuery({
        queryKey: bootstrapQueryKey,
        queryFn: fetchBootstrap,
      })
      const landing = getAuthenticatedLandingPath(bootstrap) ?? '/reporting'
      onNavigate?.(landing)
    } catch (error) {
      setNavError(getCompleteErrorMessage(error, 'Impossible de terminer l’onboarding.'))
      resume()
    }
  }

  return (
    <div
      className="mx-auto w-full max-w-[96rem] px-4 pb-28 pt-6 sm:px-8 lg:px-10"
      data-testid="draft-onboarding-wizard"
    >
      <div className="mb-6 space-y-3">
        <span className="inline-flex rounded-full bg-spore-moss/20 px-3 py-1 text-xs font-semibold text-spore-forest">
          ✨ Onboarding Spore
        </span>
        <h1 className="text-3xl font-semibold tracking-tight text-spore-forest sm:text-4xl">
          Configurons votre établissement
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-spore-muted sm:text-base">
          Deux étapes rapides : présentez votre établissement et ses pôles d’activité, puis invitez
          votre équipe. Vous pourrez tout modifier ensuite.
        </p>
      </div>

      <div className="mb-8 flex flex-wrap gap-2">
        <div
          className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
            step === 'structure'
              ? 'bg-spore-forest/5 font-medium text-spore-forest'
              : 'text-spore-muted'
          }`}
        >
          <span
            className={`flex size-6 items-center justify-center rounded-full text-xs ${
              step === 'team'
                ? 'bg-spore-moss/30 text-spore-forest'
                : 'bg-spore-forest text-white'
            }`}
          >
            {step === 'team' ? <Check className="size-3.5" /> : '1'}
          </span>
          Établissement — Infos & pôles
        </div>
        <div
          className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
            step === 'team' ? 'bg-spore-forest/5 font-medium text-spore-forest' : 'text-spore-muted'
          }`}
        >
          <span
            className={`flex size-6 items-center justify-center rounded-full text-xs ${
              step === 'team' ? 'bg-spore-forest text-white' : 'bg-spore-forest/10 text-spore-muted'
            }`}
          >
            2
          </span>
          Équipe — Membres & rôles
        </div>
      </div>

      <SaveStatus status={saveStatus} />

      {step === 'structure' ? (
        <StructureStep
          draft={draft}
          setDraft={updateDraft}
          catalogUnits={(catalogQuery.data ?? []).map((unit) => ({
            key: unit.key,
            label: unit.label,
            description: unit.description ?? '',
            unit_type: unit.unit_type,
          }))}
          catalogLoading={catalogQuery.isPending}
        />
      ) : (
        <TeamStepView draft={draft} setDraft={updateDraft} />
      )}

      {(navError || completeMutation.error) && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {navError ??
            getCompleteErrorMessage(completeMutation.error, 'Une erreur est survenue.')}
        </div>
      )}

      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-20 px-4 pb-4 sm:px-8">
        <div className="pointer-events-auto mx-auto flex w-full max-w-[96rem] items-center justify-between gap-4 rounded-full border border-spore-forest/10 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
          <p className="min-w-0 flex-1 truncate text-sm text-spore-muted">{stickyMessage}</p>
          <div className="flex shrink-0 items-center gap-2">
            {step === 'team' ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  className="h-10 rounded-xl"
                  disabled={isNavigating || completeMutation.isPending}
                  onClick={() => void handleBack()}
                >
                  ← Retour
                </Button>
                <Button
                  type="button"
                  className="h-10 rounded-xl bg-spore-forest text-white hover:bg-spore-moss disabled:bg-spore-moss/40"
                  disabled={!completeOk || isNavigating || completeMutation.isPending}
                  onClick={() => void handleComplete()}
                >
                  {completeMutation.isPending ? 'Activation…' : 'Terminer ✓'}
                </Button>
              </>
            ) : (
              <Button
                type="button"
                className="h-10 rounded-xl bg-spore-forest text-white hover:bg-spore-moss disabled:bg-spore-moss/40"
                disabled={!structureOk || isNavigating}
                onClick={() => void handleContinue()}
              >
                Continuer →
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
