import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const pagePath = join(dirname(fileURLToPath(import.meta.url)), '../pages/checklist-quick-create-page.tsx')

function readPage(): string {
  return readFileSync(pagePath, 'utf8')
}

describe('checklist-quick-create-page', () => {
  const source = readPage()

  it('creates flash to-do through the dedicated API hook', () => {
    expect(source).toContain('useCreateFlashTodoMutation')
    expect(source).not.toContain('useQuickCreatePersonalChecklistMutation')
    expect(source).not.toContain('quickCreatePersonalChecklistExecution')
    expect(source).not.toContain('personal-executions')
  })

  it('collects flash to-do required fields', () => {
    expect(source).toContain('ChecklistBusinessUnitSelect')
    expect(source).toContain('ActionCreateAssigneeSection')
    expect(source).toContain('validateFlashTodoCreate')
    expect(source).toContain('business_unit_id')
    expect(source).toContain('assigned_to')
  })
})
