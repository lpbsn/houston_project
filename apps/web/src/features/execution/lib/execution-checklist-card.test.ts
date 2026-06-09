import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const featureDir = dirname(fileURLToPath(import.meta.url))
const componentsDir = join(featureDir, '../components')

function readComponent(filename: string): string {
  return readFileSync(join(componentsDir, filename), 'utf8')
}

describe('execution-checklist-card', () => {
  const source = readComponent('execution-checklist-card.tsx')

  it('does not reuse Action card visual primitives', () => {
    expect(source).not.toContain('ActionDeadlineProgressBar')
    expect(source).not.toContain('terrainFeedInteractiveCardClassName')
  })

  it('uses checklist-specific visual identity', () => {
    expect(source).toContain('ClipboardCheck')
    expect(source).toContain('Clock')
    expect(source).toContain('terrainFeedCardBaseClassName')
    expect(source).toContain('role="progressbar"')
    expect(source).toContain('Progression des tâches')
  })

  it('preserves navigation and keyboard accessibility', () => {
    expect(source).toContain('onSelect(item.id)')
    expect(source).toContain('onKeyDown')
    expect(source).toContain('tabIndex={0}')
    expect(source).toContain('role="button"')
  })

  it('displays execution_source and badge labels instead of personal/shared', () => {
    expect(source).toContain('formatChecklistFeedBadgeLabel')
    expect(source).toContain('item.execution_source')
    expect(source).toContain('item.badge')
    expect(source).not.toContain('checklist_type')
    expect(source).not.toContain('Partagée')
    expect(source).not.toContain('Personnelle')
    expect(source).toContain('item.business_unit_label')
    expect(source).toContain('item.assigned_to_display_name')
    expect(source).toContain('formatChecklistExecutionStatusLabel')
    expect(source).toContain('formatChecklistProgressLabel')
    expect(source).toContain('formatChecklistEndBeforeTimeLabel')
    expect(source).not.toContain('formatChecklistEndAtLabel')
    expect(source).not.toContain('toLocaleString')
    expect(source).toContain('EN RETARD')
    expect(source).toContain('item.is_overdue')
  })
})
