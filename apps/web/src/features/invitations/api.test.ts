import { beforeEach, describe, expect, it, vi } from 'vitest'

const acceptInvitationSession = vi.hoisted(() => vi.fn())

vi.mock('@/features/auth/api', () => {
  class AuthApiError extends Error {
    status: number
    code: string | null

    constructor(message: string, status: number, code: string | null = null) {
      super(message)
      this.status = status
      this.code = code
    }
  }

  return {
    AuthApiError,
    acceptInvitationSession,
  }
})

import { AuthApiError } from '@/features/auth/api'
import { InvitationAcceptApiError, acceptDirectorInvitation } from './api'

describe('invitation auth boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('delegates session transport and persistence entirely to Auth', async () => {
    acceptInvitationSession.mockResolvedValueOnce(undefined)

    await expect(
      acceptDirectorInvitation('invite-token', {
        password: 'secret',
        password_confirmation: 'secret',
      }),
    ).resolves.toBeUndefined()

    expect(acceptInvitationSession).toHaveBeenCalledWith('invite-token', {
      password: 'secret',
      password_confirmation: 'secret',
    })
  })

  it('preserves invitation error status and code', async () => {
    acceptInvitationSession.mockRejectedValueOnce(
      new AuthApiError('Invitation expired.', 400, 'invitation_expired'),
    )

    const promise = acceptDirectorInvitation('invite-token', {
      password: 'secret',
      password_confirmation: 'secret',
    })

    await expect(promise).rejects.toMatchObject<Partial<InvitationAcceptApiError>>({
      message: 'Invitation expired.',
      status: 400,
      code: 'invitation_expired',
    })
  })
})
