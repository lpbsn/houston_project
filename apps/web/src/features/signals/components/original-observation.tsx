import { useId, useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainCard } from '@/components/ui/terrain'
import type { SignalDetail } from '../types'

export function OriginalObservation({ signal }: { signal: SignalDetail }) {
  const [open, setOpen] = useState(false)
  const contentId = useId()
  if (!signal.can_view_original_observation) return null

  const original = signal.original_observation
  return (
    <TerrainCard>
      <Button type="button" variant="outline" aria-expanded={open} aria-controls={contentId}
        className="max-w-full whitespace-normal text-left text-spore-forest"
        onClick={() => setOpen(!open)}>
        {open ? 'Masquer l’observation originale' : 'Voir l’observation originale'}
      </Button>
      {open ? (
        <div id={contentId} className="mt-3 space-y-3 text-sm text-[#1a1a1a]">
          <p>Texte envoyé à l’origine de ce sujet, avant reformulation par l’IA.
            Pour un vocal, il s’agit de la transcription envoyée, pas de l’audio.</p>
          {original ? (
            <>
              <p className="font-medium">
                {original.reporter_display_name || 'Auteur non renseigné'} ·{' '}
                <time dateTime={original.submitted_at}>
                  {new Date(original.submitted_at).toLocaleString('fr-FR')}
                </time>
              </p>
              <blockquote className="whitespace-pre-wrap break-words rounded-xl border border-spore-forest/20 bg-white p-3">
                {original.raw_text}
              </blockquote>
            </>
          ) : <p>L’observation originale n’est plus disponible.</p>}
        </div>
      ) : null}
    </TerrainCard>
  )
}
