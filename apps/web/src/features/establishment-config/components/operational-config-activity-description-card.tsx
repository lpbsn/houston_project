import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  useActivityDescription,
  useUpdateActivityDescription,
} from '@/features/establishment-config/hooks'
import { resolveRuntimeConfigErrorMessage } from '@/features/establishment-config/lib/runtime-config-errors'
import { useServerText } from '@/features/establishment-config/lib/use-server-text'
import {
  ACTIVITY_DESCRIPTION_MAX_LENGTH,
  ACTIVITY_DESCRIPTION_MIN_LENGTH,
  countedTextLength,
} from '@/features/onboarding/lib/onboarding-draft-payload'

type OperationalConfigActivityDescriptionCardProps = {
  establishmentId: string
}

export function OperationalConfigActivityDescriptionCard({
  establishmentId,
}: OperationalConfigActivityDescriptionCardProps) {
  const descriptionQuery = useActivityDescription(establishmentId)
  const updateMutation = useUpdateActivityDescription(establishmentId)

  if (descriptionQuery.isPending) {
    return (
      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardContent className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" />
          Chargement de la description…
        </CardContent>
      </Card>
    )
  }

  if (descriptionQuery.error || !descriptionQuery.data) {
    return (
      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
        <CardHeader>
          <CardTitle>Description de l’établissement</CardTitle>
          <CardDescription>
            {resolveRuntimeConfigErrorMessage(
              descriptionQuery.error,
              'La description n’a pas pu être chargée.',
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="outline"
            className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            onClick={() => {
              void descriptionQuery.refetch()
            }}
          >
            Réessayer
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <ActivityDescriptionEditor
      key={establishmentId}
      establishmentId={establishmentId}
      serverDescription={descriptionQuery.data.description}
      isSaving={updateMutation.isPending}
      onSave={updateMutation.mutateAsync}
    />
  )
}

function ActivityDescriptionEditor({
  establishmentId,
  serverDescription,
  isSaving,
  onSave,
}: {
  establishmentId: string
  serverDescription: string
  isSaving: boolean
  onSave: (description: string) => Promise<{ description: string }>
}) {
  const descriptionDraft = useServerText(serverDescription, establishmentId)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const description = descriptionDraft.text
  const length = countedTextLength(description)
  const tooLong = length > ACTIVITY_DESCRIPTION_MAX_LENGTH
  const tooShort = length < ACTIVITY_DESCRIPTION_MIN_LENGTH
  const unchanged = !descriptionDraft.changed

  async function handleSave() {
    setFeedback(null)
    setErrorMessage(null)
    try {
      const saved = await onSave(description.trim())
      descriptionDraft.setText(saved.description)
      setFeedback('Description enregistrée.')
    } catch (error) {
      setErrorMessage(
        resolveRuntimeConfigErrorMessage(
          error,
          'La description n’a pas pu être enregistrée.',
        ),
      )
    }
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9]">
      <CardHeader className="gap-2">
        <CardTitle className="text-lg font-semibold">Description de l’établissement</CardTitle>
        <CardDescription className="text-sm">
          Ce texte décrit l’activité de l’établissement. Les prochaines analyses le liront tel
          qu’il est enregistré.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <label className="text-sm font-medium" htmlFor="establishment-activity-description">
            Description
          </label>
          <span className={tooLong ? 'text-xs text-destructive' : 'text-xs text-muted-foreground'}>
            {length} / {ACTIVITY_DESCRIPTION_MAX_LENGTH}
          </span>
        </div>
        <Textarea
          id="establishment-activity-description"
          value={description}
          disabled={isSaving}
          onChange={(event) => descriptionDraft.setText(event.target.value)}
          placeholder="Décrivez votre établissement : type, capacité, spécificités, positionnement…"
          className="min-h-36 rounded-[1rem] border-[#e7dfd1] bg-white"
        />
        <p className="text-sm text-muted-foreground">Entre 10 et 10 000 caractères.</p>
        {tooLong ? (
          <p className="text-sm text-destructive">
            La description dépasse 10 000 caractères. Raccourcissez-la pour l’enregistrer.
          </p>
        ) : null}
        {length > 0 && tooShort ? (
          <p className="text-sm text-destructive">
            La description doit contenir au moins 10 caractères.
          </p>
        ) : null}
        <div className="flex justify-end">
          <Button
            type="button"
            className="h-10 rounded-[1rem]"
            disabled={isSaving || tooLong || tooShort || unchanged}
            onClick={() => {
              void handleSave()
            }}
          >
            {isSaving ? <LoaderCircle className="size-4 animate-spin" /> : null}
            Enregistrer
          </Button>
        </div>
        {feedback ? <p className="text-sm text-emerald-700">{feedback}</p> : null}
        {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}
      </CardContent>
    </Card>
  )
}
