import type { ChatStatus } from '../types'

export function isChatRuntimeAvailable(status: ChatStatus | undefined): boolean {
  return Boolean(status?.can_access && status.chat_enabled)
}

export function resolveChatNavVisible(options: {
  hasOperationalAccess: boolean
  status: ChatStatus | undefined
  statusResolved: boolean
  bootstrapChatAvailable: boolean
}): boolean {
  if (!options.hasOperationalAccess) {
    return false
  }
  if (options.statusResolved) {
    return isChatRuntimeAvailable(options.status)
  }
  return options.bootstrapChatAvailable
}

export function shouldRedirectFromUnavailableChat(options: {
  isChatRoute: boolean
  statusResolved: boolean
  isRuntimeAvailable: boolean
}): boolean {
  return options.isChatRoute && options.statusResolved && !options.isRuntimeAvailable
}
