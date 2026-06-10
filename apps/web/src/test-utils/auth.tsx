import type { ReactNode } from 'react'

export const defaultBootstrapFixture = {
  active_membership: {
    id: 'mbr-viewer',
    establishment_id: 'est-1',
  },
  user: {
    username: 'viewer',
    email: 'viewer@example.com',
  },
} as const

export function createAuthProviderMock(bootstrap = defaultBootstrapFixture) {
  return {
    useAuth: () => ({ bootstrap }),
  }
}

export type AuthProviderMockProps = {
  children: ReactNode
}
