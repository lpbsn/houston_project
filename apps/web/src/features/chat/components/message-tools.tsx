import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain'
import { messageTool } from '../workspace-api'
import { chatQueryKeys } from '../api'
import type { ChatMessage } from '../types'

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
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const mutation = useMutation({
    mutationFn: (body: Parameters<typeof messageTool>[2]) =>
      messageTool(establishmentId, message.id, body),
    onSuccess: async (_, body) => {
      await client.invalidateQueries({
        queryKey: chatQueryKeys.messages(establishmentId, conversationId),
      })
      await client.invalidateQueries({
        queryKey: ['chat', 'source-message', establishmentId, message.id],
      })
      if (body.operation === 'observe') setOpen(false)
    },
  })
  return (
    <>
      <div className="mt-2 flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          disabled={mutation.isPending}
          aria-pressed={message.acknowledged ?? false}
          aria-label="Accuser réception"
          onClick={() =>
            mutation.mutate({ operation: 'acknowledge', active: !message.acknowledged })
          }
          className="rounded-full border bg-white px-3 py-1.5 text-[#114660]"
        >
          👍 {message.acknowledgement_count || ''}
        </button>
        <button
          type="button"
          disabled={message.observation_created || mutation.isPending}
          onClick={() => {
            mutation.reset()
            setText(
              `${message.author_display_name}, le ${new Date(message.created_at).toLocaleString('fr-FR')} : ${message.body}`,
            )
            setOpen(true)
          }}
          className="rounded-full border bg-white px-3 py-1.5 text-[#114660]"
        >
          {message.observation_created ? 'Observation envoyée' : 'Créer une observation'}
        </button>
      </div>
      {mutation.isError && !open && (
        <p role="alert" className="text-sm">
          {mutation.error.message}
        </p>
      )}
      <TerrainDialog open={open} title="Partager une observation" onClose={() => setOpen(false)}>
        <div className="space-y-3 text-[#1a1a1a]">
          <p className="text-sm">
            Ce texte sortira de cette conversation pour suivre les règles de visibilité des
            observations de l’établissement. Vérifiez ce que vous partagez. Les pièces jointes ne
            sont pas transférées.
          </p>
          <textarea
            aria-label="Texte de l’observation"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            className="w-full rounded-xl border p-3 text-[#1a1a1a]"
          />
          <p className={text.length > 1000 ? 'text-red-700' : 'text-[#4d4d47]'}>
            {text.length}/1 000 caractères. Raccourcissez si nécessaire ; aucun texte n’est coupé
            automatiquement.
          </p>
          {mutation.isError && <p role="alert">{mutation.error.message}</p>}
          <Button
            disabled={mutation.isPending || text.trim().length < 10 || text.length > 1000}
            onClick={() => mutation.mutate({ operation: 'observe', active: true, text })}
          >
            Confirmer le partage
          </Button>
        </div>
      </TerrainDialog>
    </>
  )
}
