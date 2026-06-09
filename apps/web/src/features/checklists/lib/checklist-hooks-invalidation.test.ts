import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const hooksPath = join(dirname(fileURLToPath(import.meta.url)), '../hooks.ts')

function readHooks(): string {
  return readFileSync(hooksPath, 'utf8')
}

describe('checklist hooks invalidation', () => {
  const source = readHooks()

  it('invalidates both shared and personal templates when checklistType is omitted', () => {
    const invalidateSurfaces = source.slice(
      source.indexOf('function invalidateChecklistSurfaces'),
      source.indexOf('function invalidateChecklistExecutionSurfaces'),
    )

    expect(invalidateSurfaces).toContain("checklistsQueryKeys.templates(establishmentId, 'shared')")
    expect(invalidateSurfaces).toContain("checklistsQueryKeys.templates(establishmentId, 'personal')")
    expect(invalidateSurfaces).toContain('if (checklistType)')
  })

  it('invalidates execution detail, checklist surfaces, and execution feed on execution mutations', () => {
    const invalidateExecution = source.slice(
      source.indexOf('function invalidateChecklistExecutionSurfaces'),
      source.indexOf('export function useChecklistTemplatesQuery'),
    )

    expect(invalidateExecution).toContain(
      'checklistsQueryKeys.executionDetail(establishmentId, executionId)',
    )
    expect(invalidateExecution).toContain('invalidateChecklistSurfaces(queryClient, establishmentId, checklistType)')
    expect(invalidateExecution).toContain('actionsQueryKeys.all')
  })

  it('routes cancel, mark-done, skip, and observation mutations through execution invalidation', () => {
    expect(source).toContain('useCancelChecklistExecutionMutation')
    expect(source).toContain('useMarkChecklistTaskDoneMutation')
    expect(source).toContain('useSkipChecklistTaskMutation')
    expect(source).toContain('useCreateChecklistTaskObservationMutation')

    const cancelMutation = source.slice(
      source.indexOf('export function useCancelChecklistExecutionMutation'),
      source.indexOf('export function useMarkChecklistTaskDoneMutation'),
    )
    const markDoneMutation = source.slice(
      source.indexOf('export function useMarkChecklistTaskDoneMutation'),
      source.indexOf('export function useSkipChecklistTaskMutation'),
    )
    const skipMutation = source.slice(
      source.indexOf('export function useSkipChecklistTaskMutation'),
      source.indexOf('export function useCreateChecklistTaskObservationMutation'),
    )
    const observationMutation = source.slice(
      source.indexOf('export function useCreateChecklistTaskObservationMutation'),
      source.length,
    )

    for (const block of [cancelMutation, markDoneMutation, skipMutation, observationMutation]) {
      expect(block).toContain('invalidateChecklistExecutionSurfaces')
    }
  })

  it('invalidates execution feed through shared checklist surface invalidation', () => {
    const invalidateSurfaces = source.slice(
      source.indexOf('function invalidateChecklistSurfaces'),
      source.indexOf('function invalidateChecklistExecutionSurfaces'),
    )
    const createTemplate = source.slice(
      source.indexOf('export function useCreateChecklistTemplateMutation'),
      source.indexOf('export function useUpdateChecklistTemplateMutation'),
    )
    const createAssignment = source.slice(
      source.indexOf('export function useCreateChecklistAssignmentMutation'),
      source.indexOf('export function useUpdateChecklistAssignmentMutation'),
    )

    expect(invalidateSurfaces).toContain('actionsQueryKeys.all')
    expect(createTemplate).toContain('invalidateChecklistSurfaces')
    expect(createAssignment).toContain('invalidateChecklistSurfaces')
  })
})
