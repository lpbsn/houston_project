import { describe, expect, it } from 'vitest'

import { RuntimeConfigApiError } from '@/features/establishment-config/api'
import {
  mapRuntimeConfigConflictMessage,
  resolveRuntimeConfigErrorMessage,
} from '@/features/establishment-config/lib/runtime-config-errors'

describe('mapRuntimeConfigConflictMessage', () => {
  it('maps known conflict codes to French messages', () => {
    expect(mapRuntimeConfigConflictMessage('last_active_business_unit')).toBe(
      'Vous devez conserver au moins un pôle actif.',
    )
    expect(mapRuntimeConfigConflictMessage('last_active_activity_subject')).toBe(
      'Chaque pôle doit conserver au moins un sujet actif.',
    )
    expect(mapRuntimeConfigConflictMessage('business_unit_has_membership_scopes')).toBe(
      'Retirez d’abord les périmètres membres associés à ce pôle avant de le retirer.',
    )
    expect(mapRuntimeConfigConflictMessage('duplicate_business_unit_key')).toBe(
      'Un pôle avec ce libellé existe déjà.',
    )
  })

  it('falls back to detail or generic message for unknown codes', () => {
    expect(mapRuntimeConfigConflictMessage(null, 'Détail serveur')).toBe('Détail serveur')
    expect(mapRuntimeConfigConflictMessage('unknown_code')).toBe('Une erreur est survenue.')
  })
})

describe('resolveRuntimeConfigErrorMessage', () => {
  it('maps RuntimeConfigApiError codes', () => {
    const error = new RuntimeConfigApiError('English detail', 409, 'last_active_business_unit')

    expect(resolveRuntimeConfigErrorMessage(error, 'Fallback')).toBe(
      'Vous devez conserver au moins un pôle actif.',
    )
  })

  it('uses fallback for non-API errors', () => {
    expect(resolveRuntimeConfigErrorMessage(new Error('boom'), 'Erreur locale')).toBe('Erreur locale')
  })
})
