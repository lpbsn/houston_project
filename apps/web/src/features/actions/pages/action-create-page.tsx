import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { ActionsApiError } from '@/features/actions/api'
import { ActionCreateAssigneeSection } from '@/features/actions/components/action-create-assignee-section'
import { ActionCreateBusinessUnitSection } from '@/features/actions/components/action-create-business-unit-section'
import { ActionCreateDeadlineSection } from '@/features/actions/components/action-create-deadline-section'
import { ActionLinkedSignalCard } from '@/features/actions/components/action-linked-signal-card'
import { ActionLinkedSignalStrip } from '@/features/actions/components/action-linked-signal-strip'
import { useCreateActionMutation } from '@/features/actions/hooks'
import {
  applyDeadlinePreset,
  buildDueAtFromParts,
  syncDeadlineFieldsFromDueAt,
  type DeadlinePreset,
} from '@/features/actions/lib/action-create-deadline'
import type { ActionCreateRequest, ScopedUserSearchResult } from '@/features/actions/types'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'
import { useSignalDetailQuery } from '@/features/signals/hooks'
import { SignalsApiError } from '@/features/signals/api'
import { shouldShowSignalCreateActionPlan } from '@/features/signals/lib/signal-create-action'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ActionCreatePageProps = {
  mode: 'linked' | 'free'
  signalId?: string
  onNavigate: (pathname: string) => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ActionsApiError || error instanceof SignalsApiError) {
    return error.detail
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Une erreur est survenue.'
}

function canCreateActionRole(role: string | undefined): boolean {
  return role === 'owner' || role === 'director' || role === 'manager'
}

export function ActionCreatePage({ mode, signalId, onNavigate }: ActionCreatePageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const role = auth.bootstrap?.active_membership?.role

  const initialDue = applyDeadlinePreset('2h', new Date())
  const initialDeadline = syncDeadlineFieldsFromDueAt(initialDue)

  const [title, setTitle] = useState('')
  const [instruction, setInstruction] = useState('')
  const [selectedPreset, setSelectedPreset] = useState<DeadlinePreset | null>('2h')
  const [dueAt, setDueAt] = useState<Date>(initialDue)
  const [limitDate, setLimitDate] = useState(initialDeadline.limitDate)
  const [limitHours, setLimitHours] = useState(initialDeadline.limitHours)
  const [limitMinutes, setLimitMinutes] = useState(initialDeadline.limitMinutes)
  const [assignedTo, setAssignedTo] = useState('')
  const [selectedUser, setSelectedUser] = useState<ScopedUserSearchResult | null>(null)
  const [responsibleBusinessUnitId, setResponsibleBusinessUnitId] = useState('')

  const detailQuery = useSignalDetailQuery(
    establishmentId,
    mode === 'linked' ? (signalId ?? null) : null,
  )

  const createMutation = useCreateActionMutation(establishmentId)

  const applyDueAtFromFields = (dateStr: string, hoursStr: string, minutesStr: string) => {
    const hours = Number.parseInt(hoursStr, 10)
    const minutes = Number.parseInt(minutesStr, 10)
    if (Number.isNaN(hours) || Number.isNaN(minutes) || !dateStr) {
      return
    }
    const next = buildDueAtFromParts(dateStr, hours, minutes)
    if (!next) {
      return
    }
    setDueAt(next)
  }

  const handlePresetChange = (preset: DeadlinePreset) => {
    const next = applyDeadlinePreset(preset, new Date())
    const synced = syncDeadlineFieldsFromDueAt(next)
    setSelectedPreset(preset)
    setDueAt(next)
    setLimitDate(synced.limitDate)
    setLimitHours(synced.limitHours)
    setLimitMinutes(synced.limitMinutes)
  }

  const handleLimitDateChange = (value: string) => {
    setLimitDate(value)
    setSelectedPreset(null)
    applyDueAtFromFields(value, limitHours, limitMinutes)
  }

  const handleLimitTimeChange = (hours: string, minutes: string) => {
    setLimitHours(hours)
    setLimitMinutes(minutes)
    setSelectedPreset(null)
    applyDueAtFromFields(limitDate, hours, minutes)
  }

  const handleAssigneeChange = (membershipId: string, user: ScopedUserSearchResult) => {
    setAssignedTo(membershipId)
    setSelectedUser(user)
  }

  const canSubmit =
    title.trim().length > 0 &&
    instruction.trim().length > 0 &&
    assignedTo.length > 0 &&
    (mode === 'linked'
      ? Boolean(signalId)
      : responsibleBusinessUnitId.trim().length > 0)

  const handleSubmit = async () => {
    if (!establishmentId || !canSubmit) {
      return
    }

    const body: ActionCreateRequest =
      mode === 'linked' && signalId
        ? {
            title: title.trim(),
            instruction: instruction.trim(),
            assigned_to: assignedTo,
            due_at: dueAt.toISOString(),
            signal: signalId,
          }
        : {
            title: title.trim(),
            instruction: instruction.trim(),
            assigned_to: assignedTo,
            due_at: dueAt.toISOString(),
            signal: null,
            responsible_business_unit_id: responsibleBusinessUnitId,
          }

    const created = await createMutation.mutateAsync(body)
    onNavigate(`/actions/${created.id}`)
  }

  if (!establishmentId) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  if (mode === 'linked') {
    if (!signalId) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message="Signal introuvable."
          onRetry={() => onNavigate('/signals')}
        />
      )
    }

    if (detailQuery.isLoading) {
      return (
        <div className="flex items-center justify-center py-16 text-[#7D7B75]">
          <LoaderCircle className="h-6 w-6 animate-spin" />
        </div>
      )
    }

    if (detailQuery.isError || !detailQuery.data) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message={getErrorMessage(detailQuery.error)}
          onRetry={() => void detailQuery.refetch()}
        />
      )
    }

    if (!shouldShowSignalCreateActionPlan(detailQuery.data.permission_hints)) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message="Vous n'avez pas la permission de créer un plan d'action."
          onRetry={() => onNavigate(`/signals/${signalId}`)}
        />
      )
    }
  } else if (!canCreateActionRole(role)) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Vous n'avez pas la permission de créer un plan d'action."
        onRetry={() => onNavigate('/execution')}
      />
    )
  }

  const errorMessage = createMutation.error ? getErrorMessage(createMutation.error) : null

  return (
    <div className="flex min-h-full flex-col">
      <form
        className="flex flex-1 flex-col"
        onSubmit={(e) => {
          e.preventDefault()
          void handleSubmit()
        }}
      >
        {mode === 'linked' && detailQuery.data ? (
          <ActionLinkedSignalStrip>
            <ActionLinkedSignalCard
              title={detailQuery.data.title}
              locationText={detailQuery.data.location_text || null}
            />
          </ActionLinkedSignalStrip>
        ) : null}

        <div className="flex flex-1 flex-col gap-3 px-3 pb-28 pt-2">
          {mode === 'linked' && detailQuery.data ? (
            <section className="flex flex-col gap-1.5">
              <TerrainSectionLabel>Classification héritée du signal</TerrainSectionLabel>
              <TerrainCard className="px-3 py-2.5">
                <SignalClassificationBadges signal={detailQuery.data} />
              </TerrainCard>
            </section>
          ) : null}

          {mode === 'free' ? (
            <ActionCreateBusinessUnitSection
              establishmentId={establishmentId}
              selectedBusinessUnitId={responsibleBusinessUnitId}
              onBusinessUnitChange={setResponsibleBusinessUnitId}
            />
          ) : null}

          <ActionCreateAssigneeSection
            establishmentId={establishmentId}
            assignedTo={assignedTo}
            selectedUser={selectedUser}
            onAssignedToChange={handleAssigneeChange}
          />

          <ActionCreateDeadlineSection
            selectedPreset={selectedPreset}
            limitDate={limitDate}
            limitHours={limitHours}
            limitMinutes={limitMinutes}
            onPresetChange={handlePresetChange}
            onLimitDateChange={handleLimitDateChange}
            onLimitTimeChange={handleLimitTimeChange}
          />

          <section className="flex flex-col gap-1.5">
            <TerrainSectionLabel>Titre</TerrainSectionLabel>
            <TerrainCard>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex. Vérifier la climatisation"
                className="border-0 bg-transparent p-0 text-[15px] shadow-none focus-visible:ring-0"
                required
              />
            </TerrainCard>
          </section>

          <section className="flex flex-col gap-1.5">
            <TerrainSectionLabel>Consigne</TerrainSectionLabel>
            <TerrainCard>
              <textarea
                className="min-h-[100px] w-full resize-y bg-transparent text-[14px] leading-relaxed text-[#444] outline-none placeholder:text-[#aaa]"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Décrivez la consigne pour le responsable…"
                required
              />
            </TerrainCard>
          </section>

          {errorMessage ? (
            <p className="text-sm text-destructive" role="alert">
              {errorMessage}
            </p>
          ) : null}
        </div>

        <footer
          className={cn(
            'sticky bottom-0 z-10 mt-auto shrink-0',
            'border-t border-[#E8E6DF] bg-[#F5F4F0]',
            'shadow-[0_-4px_12px_rgba(0,0,0,0.04)]',
            'px-3 pt-2.5 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
          )}
        >
          <Button
            type="submit"
            disabled={!canSubmit || createMutation.isPending}
            className={cn(
              'h-11 w-full rounded-2xl text-[15px] font-semibold text-white hover:bg-[#1B4FD8]/95',
              terrain.primaryBg,
            )}
          >
            {createMutation.isPending ? 'Création…' : 'Créer'}
          </Button>
        </footer>
      </form>
    </div>
  )
}
