import { useId, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Info } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain'
import { trackObservation } from '@/features/observations/components/observation-processing-tracker-provider'
import {
  OBSERVATION_TEXT_MAX_LENGTH,
  OBSERVATION_TEXT_MIN_LENGTH,
} from '@/features/observations/types'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'

import { messageTool } from '../workspace-api'
import { chatQueryKeys } from '../api'
import type { ChatMessage } from '../types'

const observationDialogActionClassName =
  'h-12 min-h-12 rounded-full px-[18px] text-[15px] font-bold shadow-none max-[520px]:w-full min-[521px]:min-w-[152px] min-[521px]:flex-1 min-[741px]:flex-none'

function formatObservationSourceTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} · ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function MessageTools({
  establishmentId,
  conversationId,
  message,
}: {
  establishmentId: string
  conversationId: string
  message: ChatMessage
}) {
  const client = useQueryClient()
  const auth = useAuth()
  const sourceLabelId = useId()
  const textFieldId = useId()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const fromList = (auth.bootstrap?.memberships ?? []).find(
    (membership) =>
      membership.establishment_id === establishmentId && membership.status === 'active',
  )?.id
  const active = auth.bootstrap?.active_membership
  const authorMembershipId =
    fromList ?? (active?.establishment_id === establishmentId ? active.id : null) ?? null
  const mutation = useMutation({
    mutationFn: (body: Parameters<typeof messageTool>[2]) =>
      messageTool(establishmentId, message.id, body),
    onSuccess: async (result, body) => {
      await client.invalidateQueries({
        queryKey: chatQueryKeys.messages(establishmentId, conversationId),
      })
      await client.invalidateQueries({
        queryKey: ['chat', 'source-message', establishmentId, message.id],
      })
      if (body.operation !== 'observe') {
        return
      }
      setOpen(false)
      if (result.target_id && authorMembershipId) {
        trackObservation({
          observationId: result.target_id,
          establishmentId,
          authorMembershipId,
          origin: 'direct_report',
          submittedAt: new Date().toISOString(),
        })
      }
    },
  })
  const overLimit = text.length > OBSERVATION_TEXT_MAX_LENGTH
  const canCreate =
    !mutation.isPending &&
    text.trim().length >= OBSERVATION_TEXT_MIN_LENGTH &&
    text.length <= OBSERVATION_TEXT_MAX_LENGTH

  return (
    <>
      <div className="flex flex-wrap gap-1.5 text-xs">
        <button
          type="button"
          disabled={mutation.isPending}
          aria-pressed={message.acknowledged ?? false}
          aria-label={
            message.acknowledgement_count
              ? `Accuser réception, ${message.acknowledgement_count}`
              : 'Accuser réception'
          }
          onClick={() =>
            mutation.mutate({ operation: 'acknowledge', active: !message.acknowledged })
          }
          className="inline-flex min-h-8 items-center gap-1 rounded-full border border-[#E8E6DF] bg-white px-2.5 text-[#1d5949] outline-none focus-visible:ring-2 focus-visible:ring-[#265d4c]/40"
        >
          <span aria-hidden="true">👍</span>
          {message.acknowledgement_count ? <span>{message.acknowledgement_count}</span> : null}
        </button>
        <button
          type="button"
          disabled={message.observation_created || mutation.isPending}
          onClick={() => {
            mutation.reset()
            setText(message.body)
            setOpen(true)
          }}
          className="inline-flex min-h-8 items-center rounded-full border border-[#E8E6DF] bg-white px-2.5 text-[#1d5949] outline-none focus-visible:ring-2 focus-visible:ring-[#265d4c]/40"
        >
          {message.observation_created ? 'Observation envoyée' : 'Créer une observation'}
        </button>
      </div>
      {mutation.isError && !open && (
        <p role="alert" className="text-sm">
          {mutation.error.message}
        </p>
      )}
      <TerrainDialog
        open={open}
        size="wide"
        title="Créer une observation"
        description="Le message d’origine reste visible ci-dessous. Le texte de l’observation peut être relu et ajusté avant création. Les pièces jointes ne sont pas transférées."
        onClose={() => setOpen(false)}
      >
        <div className="flex flex-col gap-[18px] text-[#242826]">
          <section
            aria-labelledby={sourceLabelId}
            className="rounded-[18px] border border-[#e6e7e2] bg-[#f8f8f6] p-[18px] min-[741px]:rounded-[22px]"
          >
            <p
              id={sourceLabelId}
              className="mb-3 text-xs leading-none font-bold tracking-[0.12em] text-[#8c948c] uppercase"
            >
              Message d’origine
            </p>
            <div className="mb-2.5 flex flex-wrap items-center gap-3 max-[520px]:items-start max-[520px]:gap-2.5">
              <span
                aria-hidden="true"
                className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-[#dbe8e1] text-sm font-bold text-[#245d4a]"
              >
                {getDisplayNameInitials(message.author_display_name)}
              </span>
              <div>
                <p className="text-base leading-tight font-bold">{message.author_display_name}</p>
                <p className="text-sm leading-snug text-[#6f776f]">
                  {formatObservationSourceTimestamp(message.created_at)}
                </p>
              </div>
            </div>
            <div className="rounded-2xl border border-[#e6e7e2] bg-white px-[18px] py-4 text-[15px] leading-[1.55] wrap-break-word whitespace-pre-wrap min-[521px]:text-base">
              {message.body}
            </div>
          </section>

          <div className="overflow-hidden rounded-[18px] border border-[#e6e7e2] bg-white min-[741px]:rounded-[22px]">
            <div className="flex items-center justify-between gap-4 px-[18px] pt-4">
              <label
                htmlFor={textFieldId}
                className="text-xs leading-none font-bold tracking-[0.12em] text-[#8c948c] uppercase"
              >
                Texte de l’observation
              </label>
              <p
                className={cn(
                  'text-sm tabular-nums',
                  overLimit ? 'font-semibold text-red-700' : 'text-[#6f776f]',
                )}
              >
                {text.length.toLocaleString('fr-FR')} /{' '}
                {OBSERVATION_TEXT_MAX_LENGTH.toLocaleString('fr-FR')}
              </p>
            </div>
            <textarea
              id={textFieldId}
              aria-label="Texte de l’observation"
              aria-invalid={overLimit}
              value={text}
              onChange={(event) => setText(event.target.value)}
              className="min-h-[148px] w-full resize-y border-0 bg-transparent px-[18px] pt-3 pb-4 font-[inherit] text-base leading-normal text-[#242826] outline-none min-[521px]:min-h-[168px] min-[521px]:text-[17px] min-[741px]:min-h-[196px] min-[741px]:text-lg"
            />
            <div className="flex flex-col gap-3 px-[18px] pb-4">
              {overLimit ? (
                <p role="alert" className="text-sm text-red-700">
                  Raccourcissez le texte. Aucun caractère n’est coupé automatiquement.
                </p>
              ) : null}
              <div className="flex items-start gap-2.5 rounded-2xl border border-[#ece3cd] bg-[#faf7ef] px-4 py-[15px] text-sm leading-normal text-[#5f5a4c]">
                <Info
                  className="mt-px size-[18px] shrink-0 text-[#8A7E59]"
                  aria-hidden="true"
                  strokeWidth={1.8}
                />
                <p>
                  Cette observation suivra les règles de visibilité de l’établissement. Vérifiez le
                  contenu avant validation.
                </p>
              </div>
            </div>
          </div>

          {mutation.isError ? (
            <p role="alert" className="text-sm text-red-700">
              {mutation.error.message}
            </p>
          ) : null}

          <div className="mt-1.5 flex flex-col gap-3 max-[520px]:mt-0.5 min-[521px]:flex-row min-[521px]:flex-wrap min-[521px]:justify-end">
            <Button
              type="button"
              variant="outline"
              className={cn(
                observationDialogActionClassName,
                'border-[#d9dbd5] bg-white text-[#242826] hover:bg-[#f8f8f6]',
              )}
              onClick={() => setOpen(false)}
            >
              Annuler
            </Button>
            <Button
              type="button"
              className={cn(
                observationDialogActionClassName,
                'border-transparent bg-[#245d4a] text-white hover:bg-[#1e5342]',
              )}
              disabled={!canCreate}
              onClick={() => mutation.mutate({ operation: 'observe', active: true, text })}
            >
              Créer l’observation
            </Button>
          </div>
        </div>
      </TerrainDialog>
    </>
  )
}
