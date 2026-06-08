import { describe, expect, it } from 'vitest'

import { parseStandardApiError } from './api-errors'

describe('parseStandardApiError', () => {
  it('extracts detail and code from API error payloads', () => {
    const result = parseStandardApiError(
      new Response(null, { status: 403 }),
      { detail: 'Forbidden.', code: 'permission_denied' },
    )

    expect(result).toEqual({
      status: 403,
      detail: 'Forbidden.',
      code: 'permission_denied',
    })
  })

  it('falls back when payload is missing fields', () => {
    const result = parseStandardApiError(new Response(null, { status: 500 }), null)

    expect(result).toEqual({
      status: 500,
      detail: 'Une erreur est survenue.',
      code: null,
    })
  })
})
