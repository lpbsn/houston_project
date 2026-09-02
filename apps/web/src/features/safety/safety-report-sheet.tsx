import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'

import { SafetyApiError, createContentReport, type ContentReportKind } from './api'

type SafetyReportSheetProps = {
  open: boolean
  establishmentId: string | null
  contentKind: ContentReportKind
  targetMembershipId?: string
  contentId?: string
  onClose: () => void
  onReported?: () => void
}

export function SafetyReportSheet({
  open,
  establishmentId,
  contentKind,
  targetMembershipId,
  contentId,
  onClose,
  onReported,
}: SafetyReportSheetProps) {
  const [reason, setReason] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function submit() {
    if (!establishmentId) {
      return
    }
    setPending(true)
    setError(null)
    try {
      await createContentReport(establishmentId, {
        content_kind: contentKind,
        reason,
        target_membership_id: targetMembershipId,
        content_id: contentId,
      })
      setDone(true)
      onReported?.()
    } catch (caught) {
      setError(caught instanceof SafetyApiError ? caught.detail : 'Signalement impossible.')
    } finally {
      setPending(false)
    }
  }

  return (
    <TerrainBottomSheet title="Signaler" open={open} onClose={onClose}>
      {done ? (
        <p className="text-sm text-[#5c5a54]">Signalement enregistré.</p>
      ) : (
        <div className="space-y-3">
          <textarea
            className="min-h-24 w-full rounded-xl border border-[#E8E6DF] px-3 py-2 text-sm"
            placeholder="Pourquoi signalez-vous ceci ?"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          {error ? <p className="text-sm text-[#E24B4A]">{error}</p> : null}
          <Button
            className="h-11 w-full rounded-xl"
            disabled={pending || reason.trim().length === 0}
            onClick={() => void submit()}
          >
            {pending ? 'Envoi...' : 'Envoyer'}
          </Button>
        </div>
      )}
    </TerrainBottomSheet>
  )
}
