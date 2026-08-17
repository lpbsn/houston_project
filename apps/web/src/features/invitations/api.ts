import { AuthApiError, acceptInvitationSession } from '@/features/auth/api'
import type { DirectorInvitationAcceptInput } from '@/features/auth/types'

class InvitationAcceptApiError extends Error {
  status: number
  code: string | null

  constructor(message: string, status: number, code: string | null = null) {
    super(message)
    this.name = 'InvitationAcceptApiError'
    this.status = status
    this.code = code
  }
}

export async function acceptDirectorInvitation(
  token: string,
  input: DirectorInvitationAcceptInput,
) {
  try {
    await acceptInvitationSession(token, input)
  } catch (error) {
    if (!(error instanceof AuthApiError)) {
      throw error
    }
    throw new InvitationAcceptApiError(
      error.message,
      error.status,
      error.code,
    )
  }
}

export { InvitationAcceptApiError }
