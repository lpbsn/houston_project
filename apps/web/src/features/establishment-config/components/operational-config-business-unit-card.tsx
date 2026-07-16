import { LoaderCircle, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { BusinessUnitTreeItem } from '@/features/establishment-config/api'
import {
  useCreateRuntimeActivitySubject,
  useDeactivateRuntimeActivitySubject,
  useDeactivateRuntimeBusinessUnit,
  useReactivateRuntimeActivitySubject,
  useReactivateRuntimeBusinessUnit,
  useUpdateRuntimeBusinessUnit,
} from '@/features/establishment-config/hooks'
import { resolveRuntimeConfigErrorMessage } from '@/features/establishment-config/lib/runtime-config-errors'

const DESCRIPTION_MAX_LENGTH = 500

type OperationalConfigBusinessUnitCardProps = {
  businessUnit: BusinessUnitTreeItem
  establishmentId: string
  canRemoveBusinessUnit: boolean
}

export function OperationalConfigBusinessUnitCard({
  businessUnit,
  establishmentId,
  canRemoveBusinessUnit,
}: OperationalConfigBusinessUnitCardProps) {
  const [description, setDescription] = useState(businessUnit.instance_description)
  const [specificName, setSpecificName] = useState(businessUnit.specific_name)
  const [subjectLabel, setSubjectLabel] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const updateMutation = useUpdateRuntimeBusinessUnit(establishmentId)
  const deactivateBuMutation = useDeactivateRuntimeBusinessUnit(establishmentId)
  const reactivateBuMutation = useReactivateRuntimeBusinessUnit(establishmentId)
  const createSubjectMutation = useCreateRuntimeActivitySubject(establishmentId)
  const deactivateSubjectMutation = useDeactivateRuntimeActivitySubject(establishmentId)
  const reactivateSubjectMutation = useReactivateRuntimeActivitySubject(establishmentId)

  const isBusy =
    updateMutation.isPending ||
    deactivateBuMutation.isPending ||
    reactivateBuMutation.isPending ||
    createSubjectMutation.isPending ||
    deactivateSubjectMutation.isPending ||
    reactivateSubjectMutation.isPending

  async function handleSave() {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await updateMutation.mutateAsync({
        businessUnitId: businessUnit.id,
        input: {
          specific_name: specificName.trim(),
          instance_description: description.trim(),
        },
      })
      setFeedback('Pôle enregistré.')
    } catch (error) {
      setErrorMessage(
        resolveRuntimeConfigErrorMessage(error, 'Le pôle n’a pas pu être enregistré.'),
      )
    }
  }

  async function handleAddSubject() {
    const label = subjectLabel.trim()
    if (!label) {
      return
    }

    setFeedback(null)
    setErrorMessage(null)

    try {
      await createSubjectMutation.mutateAsync({
        businessUnitId: businessUnit.id,
        input: { label },
      })
      setSubjectLabel('')
      setFeedback('Sujet ajouté.')
    } catch (error) {
      setErrorMessage(resolveRuntimeConfigErrorMessage(error, 'Le sujet n’a pas pu être ajouté.'))
    }
  }

  async function handleRemoveSubject(subjectId: string) {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await deactivateSubjectMutation.mutateAsync(subjectId)
      setFeedback('Sujet retiré.')
    } catch (error) {
      setErrorMessage(resolveRuntimeConfigErrorMessage(error, 'Le sujet n’a pas pu être retiré.'))
    }
  }

  async function handleReactivateSubject(subjectId: string) {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await reactivateSubjectMutation.mutateAsync(subjectId)
      setFeedback('Sujet réactivé.')
    } catch (error) {
      setErrorMessage(
        resolveRuntimeConfigErrorMessage(error, 'Le sujet n’a pas pu être réactivé.'),
      )
    }
  }

  async function handleRemoveBusinessUnit() {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await deactivateBuMutation.mutateAsync(businessUnit.id)
      setFeedback('Pôle retiré.')
    } catch (error) {
      setErrorMessage(resolveRuntimeConfigErrorMessage(error, 'Le pôle n’a pas pu être retiré.'))
    }
  }

  async function handleReactivateBusinessUnit() {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await reactivateBuMutation.mutateAsync(businessUnit.id)
      setFeedback('Pôle réactivé.')
    } catch (error) {
      setErrorMessage(resolveRuntimeConfigErrorMessage(error, 'Le pôle n’a pas pu être réactivé.'))
    }
  }

  const isInactive = businessUnit.active === false

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              {businessUnit.generic.unit_type === 'transversal' ? 'Transversal' : 'Dédié'}
            </Badge>
            <CardTitle className="text-xl font-semibold">{businessUnit.specific_name}</CardTitle>
            <CardDescription className="text-sm">
              {businessUnit.generic.label}
              {isInactive ? ' · Inactif' : ''}
            </CardDescription>
          </div>
          {isInactive ? (
            <Button
              type="button"
              variant="outline"
              className="h-10 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
              disabled={isBusy}
              onClick={() => {
                void handleReactivateBusinessUnit()
              }}
            >
              {reactivateBuMutation.isPending ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : null}
              Réactiver
            </Button>
          ) : canRemoveBusinessUnit ? (
            <Button
              type="button"
              variant="outline"
              className="h-10 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
              disabled={isBusy}
              onClick={() => {
                void handleRemoveBusinessUnit()
              }}
            >
              {deactivateBuMutation.isPending ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              Retirer le pôle
            </Button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor={`name-${businessUnit.id}`}>
            Nom d’instance
          </label>
          <Input
            id={`name-${businessUnit.id}`}
            value={specificName}
            disabled={isBusy || isInactive}
            onChange={(event) => setSpecificName(event.target.value)}
            className="h-11 rounded-[1rem] border-[#e7dfd1] bg-white"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor={`description-${businessUnit.id}`}>
            Description d’instance
          </label>
          <Textarea
            id={`description-${businessUnit.id}`}
            value={description}
            maxLength={DESCRIPTION_MAX_LENGTH}
            disabled={isBusy || isInactive}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Décrivez le rôle opérationnel de ce pôle…"
            className="min-h-28 rounded-[1rem] border-[#e7dfd1] bg-white"
          />
          <div className="flex justify-end">
            <Button
              type="button"
              className="h-10 rounded-[1rem]"
              disabled={
                isBusy ||
                isInactive ||
                (specificName.trim() === businessUnit.specific_name.trim() &&
                  description.trim() === businessUnit.instance_description.trim())
              }
              onClick={() => {
                void handleSave()
              }}
            >
              {updateMutation.isPending ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : null}
              Enregistrer
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <h3 className="text-sm font-medium">Sujets opérationnels</h3>
            <p className="text-sm text-muted-foreground">
              Chaque pôle actif doit conserver au moins un sujet actif.
            </p>
          </div>

          {businessUnit.activity_subjects.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {businessUnit.activity_subjects.map((subject) => {
                const subjectInactive = subject.active === false
                const activeSubjectCount = businessUnit.activity_subjects.filter(
                  (item) => item.active !== false,
                ).length
                return (
                  <li key={subject.id}>
                    <div
                      className={`flex items-center gap-2 rounded-full border px-3 py-2 text-sm ${
                        subjectInactive
                          ? 'border-dashed border-[#ece5da] bg-[#f7f3eb] text-muted-foreground'
                          : 'border-[#ece5da] bg-white'
                      }`}
                    >
                      <span>
                        {subject.label}
                        {subjectInactive ? ' · Inactif' : ''}
                      </span>
                      {subjectInactive ? (
                        <button
                          type="button"
                          disabled={isBusy || isInactive}
                          className="rounded-full px-2 py-0.5 text-xs text-[color:var(--primary)] transition hover:bg-[color:var(--primary)]/10 disabled:opacity-40"
                          aria-label={`Réactiver ${subject.label}`}
                          onClick={() => {
                            void handleReactivateSubject(subject.id)
                          }}
                        >
                          {reactivateSubjectMutation.isPending ? (
                            <LoaderCircle className="size-3.5 animate-spin" />
                          ) : (
                            'Réactiver'
                          )}
                        </button>
                      ) : (
                        <button
                          type="button"
                          disabled={isBusy || isInactive || activeSubjectCount <= 1}
                          className="rounded-full p-1 text-muted-foreground transition hover:text-destructive disabled:opacity-40"
                          aria-label={`Retirer ${subject.label}`}
                          onClick={() => {
                            void handleRemoveSubject(subject.id)
                          }}
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Aucun sujet.</p>
          )}

          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={subjectLabel}
              disabled={isBusy || isInactive}
              onChange={(event) => setSubjectLabel(event.target.value)}
              placeholder="Ajouter un sujet…"
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-white"
            />
            <Button
              type="button"
              variant="outline"
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2] sm:shrink-0"
              disabled={isBusy || isInactive || !subjectLabel.trim()}
              onClick={() => {
                void handleAddSubject()
              }}
            >
              {createSubjectMutation.isPending ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : null}
              Ajouter
            </Button>
          </div>
        </div>

        {feedback ? <p className="text-sm text-emerald-700">{feedback}</p> : null}
        {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}
      </CardContent>
    </Card>
  )
}
