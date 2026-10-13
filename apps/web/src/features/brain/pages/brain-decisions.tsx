import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { listMemberships } from '@/features/auth/api'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'

import {
  BrainApiError,
  convertBrainSuggestion,
  decideBrainObjective,
  reviseBrainMechanism,
  reviseBrainSuggestion,
  type BrainAnalysisDetail,
  type BrainMechanism,
  type BrainObjective,
  type BrainSuggestion,
} from '../api'
import {
  errorDetail,
  OBJECTIVE_DECISION_LABELS,
  OUTCOME_LABELS,
} from '../display'

type BrainDecisionsProps = {
  establishmentId: string
  analysis: BrainAnalysisDetail | null
  objectives: BrainObjective[]
  onChanged: () => void
}

export function BrainDecisions({
  establishmentId,
  analysis,
  objectives,
  onChanged,
}: BrainDecisionsProps) {
  const evaluations = analysis?.evaluations ?? []
  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold">Suggestions</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Une suggestion devient un plan seulement après confirmation. Aucun plan n&apos;est créé
          automatiquement.
        </p>
        {analysis && analysis.suggestions.length > 0 ? (
          <div className="mt-3 flex flex-col gap-4">
            {analysis.suggestions.map((suggestion) => (
              <SuggestionEditor
                key={`${suggestion.id}:${suggestion.current_revision_id ?? ''}`}
                establishmentId={establishmentId}
                suggestion={suggestion}
                onChanged={onChanged}
              />
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm">Aucune suggestion sur cette analyse.</p>
        )}
      </section>

      <section className="rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold">Objectifs</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Un plan terminé et un objectif atteint sont deux décisions distinctes.
        </p>
        {evaluations.length > 0 ? (
          <div className="mt-3">
            <h3 className="text-sm font-medium">Évaluations de cette analyse</h3>
            <ul className="mt-2 flex flex-col gap-2 text-sm">
              {evaluations.map((evaluation) => (
                <li key={evaluation.id}>
                  {evaluation.indicator} — {OUTCOME_LABELS[evaluation.outcome] ?? evaluation.outcome}
                  {evaluation.is_current_bilan ? ' — bilan affiché' : ' — lecture historique'}
                  {evaluation.reason ? ` — ${evaluation.reason}` : ''}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {objectives.length === 0 ? (
          <p className="mt-3 text-sm">Aucun objectif vivant.</p>
        ) : (
          <div className="mt-3 flex flex-col gap-4">
            {objectives.map((objective) => (
              <ObjectiveDecision
                key={`${objective.id}:${objective.current_revision_id}`}
                establishmentId={establishmentId}
                objective={objective}
                onChanged={onChanged}
              />
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold">Knowledge</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          La formulation globale se prépare ici. L&apos;approbation et l&apos;activation sont deux
          actions distinctes, réservées à la plateforme. Le dossier privé n&apos;y est pas chargé.
        </p>
        {analysis && analysis.mechanisms.length > 0 ? (
          <div className="mt-3 flex flex-col gap-4">
            {analysis.mechanisms.map((mechanism) => (
              <MechanismDraft
                key={mechanism.id}
                establishmentId={establishmentId}
                mechanism={mechanism}
                onChanged={onChanged}
              />
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm">Aucun mécanisme à préparer.</p>
        )}
      </section>
    </div>
  )
}

function SuggestionEditor({
  establishmentId,
  suggestion,
  onChanged,
}: {
  establishmentId: string
  suggestion: BrainSuggestion
  onChanged: () => void
}) {
  const memberships = useQuery({
    queryKey: ['brain', establishmentId, 'memberships'],
    queryFn: () => listMemberships(establishmentId),
  })
  const poles = useBusinessUnitTreeQuery(establishmentId)
  const [title, setTitle] = useState(suggestion.title)
  const [description, setDescription] = useState(suggestion.description)
  const [tasks, setTasks] = useState(() =>
    suggestion.tasks.map((task) => (typeof task.task === 'string' ? task.task : '')),
  )
  const [assigneeId, setAssigneeId] = useState(() => firstId(suggestion.assignees, 'membership_id'))
  const [poleId, setPoleId] = useState(
    suggestion.pilot_business_unit_id ?? firstId(suggestion.assignees, 'business_unit_id'),
  )
  const [requiresValidation, setRequiresValidation] = useState(suggestion.requires_validation)
  const [startAt, setStartAt] = useState(localDateTimeInput(suggestion.start_at))
  const [endAt, setEndAt] = useState(localDateTimeInput(suggestion.end_at))
  const [occurrenceDate, setOccurrenceDate] = useState(suggestion.occurrence_date ?? '')
  const [allDay, setAllDay] = useState(suggestion.all_day)
  const [relatedPlanIds, setRelatedPlanIds] = useState<string[]>([])
  const revisionId = suggestion.current_revision_id

  const revise = useMutation({
    mutationFn: () => {
      if (!revisionId) {
        throw new Error('La suggestion n’a pas de révision à confirmer.')
      }
      return reviseBrainSuggestion(establishmentId, suggestion.id, {
        expected_revision_id: revisionId,
        title,
        description,
        tasks: tasks
          .map((task) => task.trim())
          .filter(Boolean)
          .map((task, index) => ({
            task,
            description: '',
            business_unit_id: poleId || null,
            position: index + 1,
          })),
        pilot_business_unit_id: poleId || null,
        assignees:
          assigneeId && poleId
            ? [{ membership_id: assigneeId, business_unit_id: poleId }]
            : [],
        all_day: allDay,
        requires_validation: requiresValidation,
        start_at: inputToIso(startAt),
        end_at: inputToIso(endAt),
        occurrence_date: occurrenceDate || null,
      })
    },
    onSuccess: () => {
      onChanged()
    },
  })
  const convert = useMutation({
    mutationFn: () => {
      if (!revisionId) {
        throw new Error('La suggestion n’a pas de révision à confirmer.')
      }
      return convertBrainSuggestion(establishmentId, suggestion.id, revisionId)
    },
    onSuccess: (result) => {
      setRelatedPlanIds(result.related_plan_ids)
      onChanged()
    },
    onError: (error) => {
      if (error instanceof BrainApiError && error.code === 'suggestion_revision_conflict') {
        onChanged()
      }
    },
  })

  if (suggestion.action_plan_id) {
    return (
      <article className="rounded-lg bg-muted/40 p-3 text-sm">
        <h3 className="font-medium">{suggestion.title}</h3>
        <p className="mt-1">Cette suggestion a déjà été convertie.</p>
        <a className="underline" href={`/action-plans/${suggestion.action_plan_id}`}>
          Ouvrir le plan
        </a>
      </article>
    )
  }

  const activeMemberships = (memberships.data ?? []).filter((item) => item.status === 'active')
  const conflict =
    (revise.error instanceof BrainApiError && revise.error.code === 'suggestion_revision_conflict') ||
    (convert.error instanceof BrainApiError && convert.error.code === 'suggestion_revision_conflict')

  return (
    <form
      className="flex flex-col gap-3 rounded-lg bg-muted/40 p-3"
      onSubmit={(event) => {
        event.preventDefault()
        revise.mutate()
      }}
    >
      <label className="flex flex-col gap-1 text-sm">
        Titre
        <Input value={title} onChange={(event) => setTitle(event.target.value)} required />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Description
        <Textarea value={description} onChange={(event) => setDescription(event.target.value)} />
      </label>
      <div className="flex flex-col gap-2">
        <p className="text-sm">Tâches</p>
        {tasks.map((task, index) => (
          <Input
            key={index}
            value={task}
            aria-label={`Tâche ${index + 1}`}
            onChange={(event) =>
              setTasks((current) => current.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))
            }
          />
        ))}
        <Button type="button" variant="outline" onClick={() => setTasks((current) => [...current, ''])}>
          Ajouter une tâche
        </Button>
      </div>
      <label className="flex flex-col gap-1 text-sm">
        Responsable
        <select
          className="h-11 rounded-xl border border-border/70 bg-background px-3 text-sm"
          value={assigneeId}
          onChange={(event) => setAssigneeId(event.target.value)}
        >
          <option value="">Choisir</option>
          {activeMemberships.map((membership) => (
            <option key={membership.id} value={membership.id}>
              {membership.user.display_name}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Pôle
        <select
          className="h-11 rounded-xl border border-border/70 bg-background px-3 text-sm"
          value={poleId}
          onChange={(event) => setPoleId(event.target.value)}
        >
          <option value="">Choisir</option>
          {(poles.data?.business_units ?? []).map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.specific_name || unit.generic.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Début
        <Input type="datetime-local" value={startAt} onChange={(event) => setStartAt(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Fin
        <Input type="datetime-local" value={endAt} onChange={(event) => setEndAt(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Date d&apos;occurrence
        <Input type="date" value={occurrenceDate} onChange={(event) => setOccurrenceDate(event.target.value)} />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={allDay}
          onChange={(event) => setAllDay(event.target.checked)}
        />
        Journée entière
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={requiresValidation}
          onChange={(event) => setRequiresValidation(event.target.checked)}
        />
        Validation requise
      </label>
      {conflict ? (
        <p className="text-sm">Une révision plus récente existe. Le formulaire a été rechargé.</p>
      ) : null}
      {revise.error && !conflict ? <p className="text-sm">{errorDetail(revise.error)}</p> : null}
      {convert.error && !conflict ? <p className="text-sm">{errorDetail(convert.error)}</p> : null}
      {relatedPlanIds.length > 0 ? (
        <p className="text-sm">
          Plans liés, non modifiés : {relatedPlanIds.join(', ')}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="outline" disabled={revise.isPending || !revisionId}>
          Enregistrer la révision
        </Button>
        <Button
          type="button"
          disabled={convert.isPending || !revisionId || !assigneeId || !poleId}
          onClick={() => convert.mutate()}
        >
          Convertir en plan
        </Button>
      </div>
    </form>
  )
}

function ObjectiveDecision({
  establishmentId,
  objective,
  onChanged,
}: {
  establishmentId: string
  objective: BrainObjective
  onChanged: () => void
}) {
  const [indicator, setIndicator] = useState(objective.indicator)
  const [target, setTarget] = useState(objective.target)
  const [method, setMethod] = useState(objective.method)
  const [justification, setJustification] = useState('')
  const decide = useMutation({
    mutationFn: (decision: 'accepted' | 'modified' | 'refused') =>
      decideBrainObjective(establishmentId, objective.id, {
        expected_revision_id: objective.current_revision_id,
        decision,
        justification,
        ...(decision === 'modified'
          ? {
              indicator,
              unit: objective.unit,
              scope: objective.scope,
              reference: objective.reference,
              target,
              due_on: objective.due_on,
              method,
            }
          : {}),
      }),
    onSuccess: onChanged,
    onError: (error) => {
      if (error instanceof BrainApiError && error.code === 'objective_revision_conflict') {
        onChanged()
      }
    },
  })
  const conflict =
    decide.error instanceof BrainApiError && decide.error.code === 'objective_revision_conflict'
  return (
    <article className="rounded-lg bg-muted/40 p-3 text-sm">
      <h3 className="font-medium">{objective.indicator}</h3>
      <p className="mt-1">
        Décision actuelle : {OBJECTIVE_DECISION_LABELS[objective.decision] ?? objective.decision}
      </p>
      {objective.current_bilan ? (
        <p className="mt-1">
          Bilan affiché : {OUTCOME_LABELS[objective.current_bilan.outcome] ?? objective.current_bilan.outcome}
          {objective.current_bilan.reason ? ` — ${objective.current_bilan.reason}` : ''}
        </p>
      ) : (
        <p className="mt-1">Aucun bilan affiché.</p>
      )}
      <label className="mt-3 flex flex-col gap-1">
        Indicateur
        <Input value={indicator} onChange={(event) => setIndicator(event.target.value)} />
      </label>
      <label className="mt-2 flex flex-col gap-1">
        Cible
        <Input value={target} onChange={(event) => setTarget(event.target.value)} />
      </label>
      <label className="mt-2 flex flex-col gap-1">
        Méthode
        <Input value={method} onChange={(event) => setMethod(event.target.value)} />
      </label>
      <label className="mt-2 flex flex-col gap-1">
        Justification
        <Textarea value={justification} onChange={(event) => setJustification(event.target.value)} />
      </label>
      {conflict ? <p className="mt-2">Une décision plus récente existe. La fiche a été rechargée.</p> : null}
      {decide.error && !conflict ? <p className="mt-2">{errorDetail(decide.error)}</p> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={() => decide.mutate('accepted')}>
          Accepter
        </Button>
        <Button type="button" variant="outline" onClick={() => decide.mutate('modified')}>
          Enregistrer la modification
        </Button>
        <Button type="button" variant="outline" onClick={() => decide.mutate('refused')}>
          Refuser
        </Button>
      </div>
    </article>
  )
}

function MechanismDraft({
  establishmentId,
  mechanism,
  onChanged,
}: {
  establishmentId: string
  mechanism: BrainMechanism
  onChanged: () => void
}) {
  const [formulation, setFormulation] = useState(mechanism.global_representation.formulation)
  const [conditions, setConditions] = useState(mechanism.global_representation.conditions)
  const [limits, setLimits] = useState(mechanism.global_representation.limits)
  const [uncertainty, setUncertainty] = useState(mechanism.global_representation.uncertainty)
  const revise = useMutation({
    mutationFn: () =>
      reviseBrainMechanism(establishmentId, mechanism.id, {
        formulation,
        conditions,
        limits,
        uncertainty,
      }),
    onSuccess: onChanged,
  })
  return (
    <form
      className="flex flex-col gap-2 text-sm"
      onSubmit={(event) => {
        event.preventDefault()
        revise.mutate()
      }}
    >
      <p>Statut : {mechanism.status}</p>
      {mechanism.formulation ? <p>Formulation d&apos;établissement : {mechanism.formulation}</p> : null}
      <label className="flex flex-col gap-1">
        Formulation globale
        <Textarea value={formulation} onChange={(event) => setFormulation(event.target.value)} required />
      </label>
      <label className="flex flex-col gap-1">
        Conditions
        <Textarea value={conditions} onChange={(event) => setConditions(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1">
        Limites
        <Textarea value={limits} onChange={(event) => setLimits(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1">
        Incertitude
        <Textarea value={uncertainty} onChange={(event) => setUncertainty(event.target.value)} />
      </label>
      {revise.error ? <p>{errorDetail(revise.error)}</p> : null}
      <Button type="submit" variant="outline" disabled={revise.isPending}>
        Préparer la formulation globale
      </Button>
    </form>
  )
}

function localDateTimeInput(value: string | null): string {
  if (!value) {
    return ''
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}T${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`
}

function inputToIso(value: string): string | null {
  if (!value) {
    return null
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }
  return parsed.toISOString()
}

function firstId(items: { [key: string]: unknown }[], key: string): string {
  const value = items[0]?.[key]
  return typeof value === 'string' ? value : ''
}
