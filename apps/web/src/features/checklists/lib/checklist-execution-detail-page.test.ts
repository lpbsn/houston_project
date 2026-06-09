import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const pagesDir = join(dirname(fileURLToPath(import.meta.url)), '../pages')

function readPage(filename: string): string {
  return readFileSync(join(pagesDir, filename), 'utf8')
}

describe('checklist-execution-detail-page permission gating', () => {
  const source = readPage('checklist-execution-detail-page.tsx')

  it('reads permission hints from execution detail payload', () => {
    expect(source).toContain('const permissionHints = execution.permission_hints')
  })

  it('gates task actions through canShowChecklistExecutionTaskActions', () => {
    expect(source).toContain('canShowChecklistExecutionTaskActions')
    expect(source).toMatch(
      /canShowChecklistExecutionTaskActions\(permissionHints,\s*\{[\s\S]*isTerminal[\s\S]*task/,
    )
    expect(source).toContain('Marquer terminée')
    expect(source).toContain('Passer la tâche')
    expect(source).toContain('Signaler')
  })

  it('gates cancel through canShowChecklistExecutionCancel', () => {
    expect(source).toContain('canShowChecklistExecutionCancel')
    expect(source).toMatch(
      /const showCancel = canShowChecklistExecutionCancel\(permissionHints,\s*\{\s*isTerminal\s*\}\)/,
    )
    expect(source).toContain('{showCancel ?')
    expect(source).toContain('Annuler l&apos;exécution')
  })

  it('does not render task action buttons outside the permission guard', () => {
    const taskActionsBlock = source.slice(
      source.indexOf('canShowChecklistExecutionTaskActions'),
      source.indexOf('skipTaskId === task.id'),
    )

    expect(taskActionsBlock).toContain('Marquer terminée')
    expect(taskActionsBlock).toContain(') ? (')
    expect(source).not.toMatch(/Marquer terminée[\s\S]*\)\s*:\s*null[\s\S]*canShowChecklistExecutionTaskActions/)
  })

  it('treats done and canceled executions as terminal for gating context', () => {
    expect(source).toContain("execution.status === 'done' || execution.status === 'canceled'")
    expect(source).toContain('isTerminal')
  })
})
