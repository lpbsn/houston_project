import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const featureDir = dirname(fileURLToPath(import.meta.url))
const pagesDir = join(featureDir, '../pages')

function readPage(filename: string): string {
  return readFileSync(join(pagesDir, filename), 'utf8')
}

describe('execution-feed-page', () => {
  const source = readPage('execution-feed-page.tsx')

  it('splits checklists from actions before rendering sections', () => {
    expect(source).toContain('splitExecutionFeedItems')
    expect(source).toContain('groupExecutionActionsBySection')
    expect(source).not.toContain('groupExecutionFeedBySection')
  })

  it('renders checklist cards before action sections', () => {
    const renderBlock = source.slice(source.indexOf('feedQuery.isSuccess'))
    const checklistIndex = renderBlock.indexOf('<ExecutionChecklistCard')
    const sectionIndex = renderBlock.indexOf('<TerrainSectionLabel')
    expect(checklistIndex).toBeGreaterThan(-1)
    expect(sectionIndex).toBeGreaterThan(-1)
    expect(checklistIndex).toBeLessThan(sectionIndex)
  })

  it('does not render checklist zone when no checklists are present', () => {
    expect(source).toContain('checklistItems.length > 0')
  })

  it('renders only action cards inside section groups', () => {
    const sectionBlock = source.slice(source.indexOf('<TerrainSectionLabel'))
    expect(sectionBlock).toContain('<ExecutionActionCard')
    expect(sectionBlock).not.toContain('<ExecutionChecklistCard')
  })

  it('preserves checklist and action navigation callbacks', () => {
    expect(source).toContain('onOpenChecklist?.(id)')
    expect(source).toContain('onOpenAction?.(id)')
  })
})
