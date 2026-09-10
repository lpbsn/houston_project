import { useMutation, useQueryClient } from '@tanstack/react-query'

import { bootstrapQueryKey, createEstablishment } from '@/features/auth/api'

export function useCreateOrganizationEstablishmentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => createEstablishment({}),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true })
    },
  })
}
