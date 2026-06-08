import { useMutation, useQueryClient } from '@tanstack/react-query'

import { businessUnitTreeQueryKey } from '@/features/auth/api'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'

import {
  createRuntimeActivitySubject,
  createRuntimeBusinessUnit,
  deactivateRuntimeActivitySubject,
  deactivateRuntimeBusinessUnit,
  updateRuntimeBusinessUnit,
} from './api'

type QueryOptions = {
  enabled?: boolean
}

export function useOperationalConfigTree(
  establishmentId: string | null | undefined,
  options?: QueryOptions,
) {
  return useBusinessUnitTreeQuery(establishmentId, options)
}

function useInvalidateOperationalConfigTree(establishmentId: string) {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({
      queryKey: businessUnitTreeQueryKey(establishmentId),
    })
  }
}

export function useCreateRuntimeBusinessUnit(establishmentId: string) {
  const invalidate = useInvalidateOperationalConfigTree(establishmentId)

  return useMutation({
    mutationFn: (input: Parameters<typeof createRuntimeBusinessUnit>[1]) =>
      createRuntimeBusinessUnit(establishmentId, input),
    onSuccess: invalidate,
  })
}

export function useUpdateRuntimeBusinessUnit(establishmentId: string) {
  const invalidate = useInvalidateOperationalConfigTree(establishmentId)

  return useMutation({
    mutationFn: ({
      businessUnitId,
      input,
    }: {
      businessUnitId: string
      input: Parameters<typeof updateRuntimeBusinessUnit>[2]
    }) => updateRuntimeBusinessUnit(establishmentId, businessUnitId, input),
    onSuccess: invalidate,
  })
}

export function useDeactivateRuntimeBusinessUnit(establishmentId: string) {
  const invalidate = useInvalidateOperationalConfigTree(establishmentId)

  return useMutation({
    mutationFn: (businessUnitId: string) =>
      deactivateRuntimeBusinessUnit(establishmentId, businessUnitId),
    onSuccess: invalidate,
  })
}

export function useCreateRuntimeActivitySubject(establishmentId: string) {
  const invalidate = useInvalidateOperationalConfigTree(establishmentId)

  return useMutation({
    mutationFn: ({
      businessUnitId,
      input,
    }: {
      businessUnitId: string
      input: Parameters<typeof createRuntimeActivitySubject>[2]
    }) => createRuntimeActivitySubject(establishmentId, businessUnitId, input),
    onSuccess: invalidate,
  })
}

export function useDeactivateRuntimeActivitySubject(establishmentId: string) {
  const invalidate = useInvalidateOperationalConfigTree(establishmentId)

  return useMutation({
    mutationFn: (activitySubjectId: string) =>
      deactivateRuntimeActivitySubject(establishmentId, activitySubjectId),
    onSuccess: invalidate,
  })
}
