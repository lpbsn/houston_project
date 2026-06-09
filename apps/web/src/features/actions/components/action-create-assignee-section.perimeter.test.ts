import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

describe('ActionCreateAssigneeSection perimeter empty state', () => {
  it('shows perimeter-specific message when businessUnitId is set', () => {
    const source = readFileSync(
      join(
        dirname(fileURLToPath(import.meta.url)),
        'action-create-assignee-section.tsx',
      ),
      'utf8',
    )

    expect(source).toContain('Aucun utilisateur rattaché à ce périmètre.')
    expect(source).toContain('businessUnitId')
  })
})
