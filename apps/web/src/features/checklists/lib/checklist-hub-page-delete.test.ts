import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const pagesDir = join(dirname(fileURLToPath(import.meta.url)), '../pages')

function readPage(filename: string): string {
  return readFileSync(join(pagesDir, filename), 'utf8')
}

describe('checklist-hub-page delete 409 flow', () => {
  const source = readPage('checklist-hub-page.tsx')

  it('resolves delete conflicts through the shared delete flow helpers', () => {
    expect(source).toContain('getActiveExecutionIdFromDeleteError')
    expect(source).toContain('resolveChecklistDeleteErrorMessage')
  })

  it('stores active execution links for delete conflicts', () => {
    expect(source).toContain('setActiveExecutionId')
    expect(source).toContain('activeExecutionId')
  })

  it('offers navigation to the in-progress execution after a 409 delete', () => {
    expect(source).toContain('Ouvrir l&apos;exécution en cours')
    expect(source).toContain('`/checklists/executions/${activeExecutionId}`')
  })

  it('clears prior delete error state before retrying delete', () => {
    const deleteHandler = source.slice(
      source.indexOf('async function handleDelete'),
      source.indexOf('const createAction'),
    )

    expect(deleteHandler).toContain('setDeleteError(null)')
    expect(deleteHandler).toContain('setActiveExecutionId(null)')
  })

  it('gates delete affordance through template permission hints in the list section', () => {
    const templateSection = readFileSync(
      join(pagesDir, '../components/checklist-template-section.tsx'),
      'utf8',
    )

    expect(templateSection).toContain('canShowChecklistTemplateDelete')
    expect(templateSection).toContain('template.permission_hints')
  })

  it('uses a single unified checklist library list', () => {
    expect(source).toContain('Bibliothèque de checklists')
    expect(source).not.toContain('Checklists partagées')
    expect(source).not.toContain('Checklists personnelles')
    expect(source).toContain("navigateTo(`/checklists/${templateId}`)")
  })
})
