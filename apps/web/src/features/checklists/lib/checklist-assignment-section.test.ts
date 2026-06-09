import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const featureDir = dirname(fileURLToPath(import.meta.url))
const componentsDir = join(featureDir, '../components')
const pagesDir = join(featureDir, '../pages')

function readComponent(filename: string): string {
  return readFileSync(join(componentsDir, filename), 'utf8')
}

function readPage(filename: string): string {
  return readFileSync(join(pagesDir, filename), 'utf8')
}

describe('checklist-assignment-section', () => {
  it('does not render assignment status badges in the management list', () => {
    const source = readComponent('checklist-assignment-section.tsx')

    expect(source).not.toContain('formatChecklistAssignmentStatusLabel')
    expect(source).not.toContain("assignment.status === 'inactive'")
    expect(source).not.toContain('Retirée')
  })

  it('shows an explicit empty state when no active assignments remain', () => {
    const source = readComponent('checklist-assignment-section.tsx')

    expect(source).toContain('Aucune affectation active.')
  })

  it('supports sticky create button placement without an inline button', () => {
    const source = readComponent('checklist-assignment-section.tsx')

    expect(source).toContain("createButtonPlacement?: 'inline' | 'sticky'")
    expect(source).toContain("createButtonPlacement === 'inline'")
    expect(source).toContain('showInlineCreateButton')
  })
})

describe('checklist-assignment-create-sticky-footer', () => {
  it('renders a sticky footer with the create assignment action', () => {
    const source = readComponent('checklist-assignment-create-sticky-footer.tsx')

    expect(source).toContain('sticky bottom-0')
    expect(source).toContain('Nouvelle affectation')
    expect(source).toContain('env(safe-area-inset-bottom)')
  })
})

describe('checklist-template-detail-page shared assignments layout', () => {
  it('places assignments before tasks and uses a sticky create footer', () => {
    const source = readPage('checklist-template-detail-page.tsx')

    expect(source).toContain('createButtonPlacement="sticky"')
    expect(source).toContain('ChecklistAssignmentCreateStickyFooter')
    expect(source).toContain('showStickyCreateFooter ? \'pb-40\' : \'pb-3\'')
    expect(source.indexOf('assignmentSection')).toBeLessThan(source.indexOf('tasksSection'))
  })
})
