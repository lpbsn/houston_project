import {
  AuthApiError,
  acceptInvitationSession,
  previewInvitation,
  type InvitationAcceptOutcome,
} from '@/features/auth/api'
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

function rethrowInvitationError(error: unknown): never {
  if (!(error instanceof AuthApiError)) {
    throw error
  }
  throw new InvitationAcceptApiError(error.message, error.status, error.code)
}

export async function previewDirectorInvitation(token: string) {
  try {
    const preview = await previewInvitation(token)
    return { requiresPassword: preview.requires_password }
  } catch (error) {
    rethrowInvitationError(error)
  }
}

export async function acceptDirectorInvitation(
  token: string,
  input: DirectorInvitationAcceptInput,
): Promise<InvitationAcceptOutcome> {
  try {
    return await acceptInvitationSession(token, input)
  } catch (error) {
    rethrowInvitationError(error)
  }
}

export { InvitationAcceptApiError }
