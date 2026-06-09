import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const hooksPath = join(dirname(fileURLToPath(import.meta.url)), '../hooks.ts')

function readHooks(): string {
  return readFileSync(hooksPath, 'utf8')
}

describe('checklist hooks invalidation', () => {
  const source = readHooks()

  it('invalidates all template list queries for an establishment', () => {
    const invalidateSurfaces = source.slice(
      source.indexOf('function invalidateChecklistSurfaces'),
      source.indexOf('function invalidateChecklistExecutionSurfaces'),
    )

    expect(invalidateSurfaces).toContain("['checklists', 'templates', establishmentId]")
    expect(invalidateSurfaces).not.toContain("'shared'")
    expect(invalidateSurfaces).not.toContain("'personal'")
  })

  it('invalidates execution detail, checklist surfaces, and execution feed on execution mutations', () => {
    const invalidateExecution = source.slice(
      source.indexOf('function invalidateChecklistExecutionSurfaces'),
      source.indexOf('export function useChecklistTemplatesQuery'),
    )

    expect(invalidateExecution).toContain(
      'checklistsQueryKeys.executionDetail(establishmentId, executionId)',
    )
    expect(invalidateExecution).toContain('invalidateChecklistSurfaces(queryClient, establishmentId)')
    expect(invalidateExecution).toContain('actionsQueryKeys.all')
  })

  it('routes cancel, mark-done, skip, and observation mutations through execution invalidation', () => {
    expect(source).toContain('useCancelChecklistExecutionMutation')
    expect(source).toContain('useMarkChecklistTaskDoneMutation')
    expect(source).toContain('useSkipChecklistTaskMutation')
    expect(source).toContain('useCreateChecklistTaskObservationMutation')
    expect(source).toContain('useCreateTemplateExecutionMutation')
  })
})
