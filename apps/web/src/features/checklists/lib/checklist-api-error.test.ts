import { describe, expect, it } from 'vitest'

import { ChecklistsApiError } from '@/features/checklists/api'

describe('ChecklistsApiError', () => {
  it('stores active execution id from conflict payload', () => {
    const error = new ChecklistsApiError({
      status: 409,
      detail: 'Une exécution est déjà en cours.',
      code: 'conflict',
      activeExecutionId: 'exec-123',
    })

    expect(error.activeExecutionId).toBe('exec-123')
    expect(error.status).toBe(409)
  })
})
