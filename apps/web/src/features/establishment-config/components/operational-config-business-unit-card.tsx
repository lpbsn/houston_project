import { LoaderCircle, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { BusinessUnitTreeItem } from '@/features/establishment-config/api'
import { RuntimeConfigApiError } from '@/features/establishment-config/api'
import {
  useCreateRuntimeActivitySubject,
  useDeactivateRuntimeActivitySubject,
  useDeactivateRuntimeBusinessUnit,
  useUpdateRuntimeBusinessUnit,
} from '@/features/establishment-config/hooks'

const DESCRIPTION_MAX_LENGTH = 500

type OperationalConfigBusinessUnitCardProps = {
  businessUnit: BusinessUnitTreeItem
  establishmentId: string
  canRemoveBusinessUnit: boolean
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof RuntimeConfigApiError) {
    return error.message
  }

  return fallback
}

export function OperationalConfigBusinessUnitCard({
  businessUnit,
  establishmentId,
  canRemoveBusinessUnit,
}: OperationalConfigBusinessUnitCardProps) {
  const [description, setDescription] = useState(businessUnit.description)
  const [subjectLabel, setSubjectLabel] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const updateMutation = useUpdateRuntimeBusinessUnit(establishmentId)
  const deactivateBuMutation = useDeactivateRuntimeBusinessUnit(establishmentId)
  const createSubjectMutation = useCreateRuntimeActivitySubject(establishmentId)
  const deactivateSubjectMutation = useDeactivateRuntimeActivitySubject(establishmentId)

  const isBusy =
    updateMutation.isPending ||
    deactivateBuMutation.isPending ||
    createSubjectMutation.isPending ||
    deactivateSubjectMutation.isPending

  async function handleSaveDescription() {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await updateMutation.mutateAsync({
        businessUnitId: businessUnit.id,
        input: { description: description.trim() },
      })
      setFeedback('Description enregistrée.')
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'La description n’a pas pu être enregistrée.'))
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
      setErrorMessage(getErrorMessage(error, 'Le sujet n’a pas pu être ajouté.'))
    }
  }

  async function handleRemoveSubject(subjectId: string) {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await deactivateSubjectMutation.mutateAsync(subjectId)
      setFeedback('Sujet retiré.')
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Le sujet n’a pas pu être retiré.'))
    }
  }

  async function handleRemoveBusinessUnit() {
    setFeedback(null)
    setErrorMessage(null)

    try {
      await deactivateBuMutation.mutateAsync(businessUnit.id)
      setFeedback('Pôle retiré.')
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Le pôle n’a pas pu être retiré.'))
    }
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              {businessUnit.unit_type === 'transversal' ? 'Transversal' : 'Dédié'}
            </Badge>
            <CardTitle className="text-xl font-semibold">{businessUnit.label}</CardTitle>
            <CardDescription className="text-sm">{businessUnit.key}</CardDescription>
          </div>
          {canRemoveBusinessUnit ? (
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
          <label className="text-sm font-medium" htmlFor={`description-${businessUnit.id}`}>
            Description libre
          </label>
          <textarea
            id={`description-${businessUnit.id}`}
            value={description}
            maxLength={DESCRIPTION_MAX_LENGTH}
            disabled={isBusy}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Décrivez le rôle opérationnel de ce pôle…"
            className="min-h-28 w-full rounded-[1rem] border border-[#e7dfd1] bg-white px-3 py-2 text-sm"
          />
          <div className="flex justify-end">
            <Button
              type="button"
              className="h-10 rounded-[1rem]"
              disabled={isBusy || description.trim() === businessUnit.description.trim()}
              onClick={() => {
                void handleSaveDescription()
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
              Chaque pôle doit conserver au moins un sujet actif.
            </p>
          </div>

          {businessUnit.activity_subjects.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {businessUnit.activity_subjects.map((subject) => (
                <li key={subject.id}>
                  <div className="flex items-center gap-2 rounded-full border border-[#ece5da] bg-white px-3 py-2 text-sm">
                    <span>{subject.label}</span>
                    <button
                      type="button"
                      disabled={isBusy || businessUnit.activity_subjects.length <= 1}
                      className="rounded-full p-1 text-muted-foreground transition hover:text-destructive disabled:opacity-40"
                      aria-label={`Retirer ${subject.label}`}
                      onClick={() => {
                        void handleRemoveSubject(subject.id)
                      }}
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Aucun sujet actif.</p>
          )}

          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={subjectLabel}
              disabled={isBusy}
              onChange={(event) => setSubjectLabel(event.target.value)}
              placeholder="Ajouter un sujet…"
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-white"
            />
            <Button
              type="button"
              variant="outline"
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2] sm:shrink-0"
              disabled={isBusy || !subjectLabel.trim()}
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
