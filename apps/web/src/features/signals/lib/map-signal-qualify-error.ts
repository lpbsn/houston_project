export type SignalQualifyErrorMapping = {
  message: string
  survivingSignalId: string | null
}

function readSurvivorId(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }
  const record = payload as Record<string, unknown>
  const survivor = record.surviving_signal_id
  if (typeof survivor === 'string' && survivor.trim().length > 0) {
    return survivor
  }
  return null
}

export function mapSignalQualifyError(options: {
  code: string | null | undefined
  detail: string | null | undefined
  payload?: unknown
}): SignalQualifyErrorMapping {
  const code = options.code ?? null
  const survivor = readSurvivorId(options.payload)

  if (code === 'already_merged') {
    return {
      message:
        survivor !== null
          ? 'Cette observation a déjà été fusionnée.'
          : 'Cette observation a déjà été fusionnée. Ouvrez l’observation survivante.',
      survivingSignalId: survivor,
    }
  }

  if (code === 'permission_denied') {
    return {
      message: 'Vous n’avez pas le droit de qualifier cette observation.',
      survivingSignalId: null,
    }
  }

  if (
    code === 'invalid_routing' ||
    code === 'invalid_business_unit' ||
    code === 'inactive_business_unit' ||
    code === 'invalid_activity_subject' ||
    code === 'inactive_activity_subject' ||
    code === 'invalid_operational_unit' ||
    code === 'inactive_operational_unit' ||
    code === 'invalid_expected_action' ||
    code === 'invalid_qualify_fields' ||
    code === 'invalid_issue_focus' ||
    code === 'signal_validation_error'
  ) {
    return {
      message: options.detail?.trim() || 'Qualification invalide. Vérifiez le pôle et le sujet.',
      survivingSignalId: null,
    }
  }

  if (code === 'invalid_signal_state') {
    return {
      message: 'Cette observation ne peut plus être qualifiée.',
      survivingSignalId: null,
    }
  }

  return {
    message: options.detail?.trim() || 'La qualification a échoué.',
    survivingSignalId: null,
  }
}
