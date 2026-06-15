import { describe, expect, it } from 'vitest'

import {
  isChatRuntimeAvailable,
  resolveChatNavVisible,
  shouldRedirectFromUnavailableChat,
} from './lib/chat-availability'
import type { ChatStatus } from './types'

const availableStatus: ChatStatus = {
  chat_enabled: true,
  can_access: true,
  can_create_dm: true,
  can_create_group: false,
  can_manage_settings: false,
}

const disabledStatus: ChatStatus = {
  chat_enabled: false,
  can_access: false,
  can_create_dm: false,
  can_create_group: false,
  can_manage_settings: true,
}

describe('chat nav availability integration', () => {
  it('shows chat nav when bootstrap is stale but runtime status is available', () => {
    expect(
      resolveChatNavVisible({
        hasOperationalAccess: true,
        status: availableStatus,
        statusResolved: true,
        bootstrapChatAvailable: false,
      }),
    ).toBe(true)
  })

  it('hides chat nav when bootstrap is stale-enabled but runtime status is disabled', () => {
    expect(
      resolveChatNavVisible({
        hasOperationalAccess: true,
        status: disabledStatus,
        statusResolved: true,
        bootstrapChatAvailable: true,
      }),
    ).toBe(false)
  })

  it('redirects away from chat routes when runtime status becomes unavailable', () => {
    expect(
      shouldRedirectFromUnavailableChat({
        isChatRoute: true,
        statusResolved: true,
        isRuntimeAvailable: false,
      }),
    ).toBe(true)
  })

  it('does not redirect while runtime status is still loading', () => {
    expect(
      shouldRedirectFromUnavailableChat({
        isChatRoute: true,
        statusResolved: false,
        isRuntimeAvailable: isChatRuntimeAvailable(undefined),
      }),
    ).toBe(false)
  })
})
