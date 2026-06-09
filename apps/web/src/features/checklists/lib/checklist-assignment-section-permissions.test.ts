import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const componentsDir = join(dirname(fileURLToPath(import.meta.url)), '../components')

function readComponent(filename: string): string {
  return readFileSync(join(componentsDir, filename), 'utf8')
}

describe('checklist-assignment-section permission gating and remove 409', () => {
  const source = readComponent('checklist-assignment-section.tsx')

  it('gates edit and remove actions through assignment permission hints', () => {
    expect(source).toContain('canShowChecklistAssignmentUpdate')
    expect(source).toContain('canShowChecklistAssignmentDeactivate')
    expect(source).toContain('assignment.permission_hints')
    expect(source).toContain('Modifier l&apos;affectation')
    expect(source).toContain('Retirer l&apos;affectation')
  })

  it('hides assignment actions when neither update nor deactivate is allowed', () => {
    expect(source).toMatch(
      /canShowChecklistAssignmentUpdate\(assignment\.permission_hints\)[\s\S]*canShowChecklistAssignmentDeactivate\(assignment\.permission_hints\)/,
    )
    expect(source).toContain(') : null}')
  })

  it('resolves assignment remove conflicts through the shared remove flow helpers', () => {
    expect(source).toContain('getActiveExecutionIdFromAssignmentRemoveError')
    expect(source).toContain('resolveChecklistAssignmentRemoveErrorMessage')
  })

  it('offers navigation to the in-progress execution after a remove conflict', () => {
    expect(source).toContain('activeExecutionId')
    expect(source).toContain('Ouvrir l&apos;exécution en cours')
    expect(source).toContain('`/checklists/executions/${activeExecutionId}`')
  })

  it('wires edit sheet only when an assignment is selected for editing', () => {
    expect(source).toContain('ChecklistAssignmentEditSheet')
    expect(source).toContain('{editingAssignment ?')
    expect(source).toContain('setEditingAssignment(assignment)')
  })
})
