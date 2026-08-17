import { useAppRoute } from '@/app/app-routes'

export function useLocationSearch(): string {
  return useAppRoute().search
}
