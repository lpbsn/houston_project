import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import { switchEstablishment } from '@/features/auth/api'
import { EstablishmentSelectorCard } from '@/features/auth/components/establishment-selector-card'

type SelectEstablishmentPageProps = {
  onNavigate: (path: string) => void
}

export function SelectEstablishmentPage({ onNavigate }: SelectEstablishmentPageProps) {
  const { memberships } = useAuth()
  const [pendingEstablishmentId, setPendingEstablishmentId] = useState<string | null>(null)
  const [selectorError, setSelectorError] = useState<string | null>(null)

  const switchMutation = useMutation({
    mutationFn: switchEstablishment,
  })

  async function handleSelectEstablishment(establishmentId: string) {
    setSelectorError(null)
    setPendingEstablishmentId(establishmentId)

    try {
      await switchMutation.mutateAsync({ establishment_id: establishmentId })
      onNavigate('/reporting')
    } catch (error) {
      setSelectorError(
        error instanceof Error ? error.message : 'Impossible de sélectionner cet établissement.',
      )
    } finally {
      setPendingEstablishmentId(null)
    }
  }

  return (
    <EstablishmentSelectorCard
      variant="post-login"
      errorMessage={selectorError}
      memberships={memberships}
      pendingEstablishmentId={pendingEstablishmentId}
      onSelect={(establishmentId) => {
        void handleSelectEstablishment(establishmentId)
      }}
    />
  )
}
