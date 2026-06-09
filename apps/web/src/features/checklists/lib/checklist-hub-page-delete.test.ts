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

  it('stores active execution links for shared and personal delete conflicts', () => {
    expect(source).toContain('setSharedActiveExecutionId')
    expect(source).toContain('setPersonalActiveExecutionId')
    expect(source).toContain('sharedActiveExecutionId')
    expect(source).toContain('personalActiveExecutionId')
  })

  it('offers navigation to the in-progress execution after a 409 delete', () => {
    expect(source).toContain('Ouvrir l&apos;exécution en cours')
    expect(source).toContain('`/checklists/executions/${sharedActiveExecutionId}`')
    expect(source).toContain('`/checklists/executions/${personalActiveExecutionId}`')
  })

  it('clears prior delete error state before retrying delete', () => {
    const sharedHandler = source.slice(
      source.indexOf('async function handleDeleteShared'),
      source.indexOf('async function handleDeletePersonal'),
    )
    const personalHandler = source.slice(
      source.indexOf('async function handleDeletePersonal'),
      source.indexOf('const createAction'),
    )

    expect(sharedHandler).toContain('setSharedDeleteError(null)')
    expect(sharedHandler).toContain('setSharedActiveExecutionId(null)')
    expect(personalHandler).toContain('setPersonalDeleteError(null)')
    expect(personalHandler).toContain('setPersonalActiveExecutionId(null)')
  })

  it('gates delete affordance through template permission hints in the list section', () => {
    const templateSection = readFileSync(
      join(pagesDir, '../components/checklist-template-section.tsx'),
      'utf8',
    )

    expect(templateSection).toContain('canShowChecklistTemplateDelete')
    expect(templateSection).toContain('template.permission_hints')
  })
})
