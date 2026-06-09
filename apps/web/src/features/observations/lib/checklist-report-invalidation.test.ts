import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const pagesDir = join(dirname(fileURLToPath(import.meta.url)), '../pages')

function readPage(filename: string): string {
  return readFileSync(join(pagesDir, filename), 'utf8')
}

describe('report-page checklist invalidation', () => {
  const source = readPage('report-page.tsx')

  it('invalidates checklist execution detail after a checklist observation submit', () => {
    const mutationBlock = source.slice(
      source.indexOf('const checklistSubmitMutation = useMutation'),
      source.indexOf('const isSubmitPending'),
    )

    expect(mutationBlock).toContain('createChecklistTaskObservation')
    expect(mutationBlock).toContain('checklistsQueryKeys.executionDetail')
    expect(mutationBlock).toContain('checklistContext.checklistExecutionId')
  })

  it('invalidates all checklist queries so feed surfaces can refetch', () => {
    const mutationBlock = source.slice(
      source.indexOf('const checklistSubmitMutation = useMutation'),
      source.indexOf('const isSubmitPending'),
    )

    expect(mutationBlock).toContain('checklistsQueryKeys.all')
  })

  it('skips checklist invalidation when checklist context is absent', () => {
    const onSuccessBlock = source.slice(
      source.indexOf('onSuccess: () => {'),
      source.indexOf('const isSubmitPending'),
    )

    expect(onSuccessBlock).toContain('if (!establishmentId || !checklistContext)')
    expect(onSuccessBlock).toContain('return')
  })
})
