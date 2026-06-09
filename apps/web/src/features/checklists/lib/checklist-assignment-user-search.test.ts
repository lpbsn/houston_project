import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const componentsDir = join(
  dirname(fileURLToPath(import.meta.url)),
  '../components',
)

function readComponent(filename: string): string {
  return readFileSync(join(componentsDir, filename), 'utf8')
}

describe('checklist assignment sheets user search wiring', () => {
  it('create sheet passes businessUnitId to shared assignment form fields', () => {
    const source = readComponent('checklist-assignment-create-sheet.tsx')

    expect(source).toContain('businessUnitId: string')
    expect(source).toMatch(
      /<ChecklistAssignmentFormFields[\s\S]*businessUnitId=\{businessUnitId\}/,
    )
  })

  it('edit sheet passes businessUnitId to shared assignment form fields', () => {
    const source = readComponent('checklist-assignment-edit-sheet.tsx')

    expect(source).toContain('businessUnitId: string')
    expect(source).toMatch(
      /<ChecklistAssignmentFormFields[\s\S]*businessUnitId=\{businessUnitId\}/,
    )
  })

  it('shared form fields pass businessUnitId to ActionCreateAssigneeSection', () => {
    const source = readComponent('checklist-assignment-form-fields.tsx')

    expect(source).toMatch(
      /<ActionCreateAssigneeSection[\s\S]*businessUnitId=\{businessUnitId\}/,
    )
  })

  it('edit sheet keeps selected assignee chip via selectedUser state', () => {
    const source = readComponent('checklist-assignment-edit-sheet.tsx')

    expect(source).toContain('buildInitialSelectedUser(assignment)')
    expect(source).toContain('selectedUser={selectedUser}')
  })
})
