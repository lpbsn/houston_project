import { describe, expect, it } from 'vitest'

import type { ChatStatus } from '../types'

import { isChatRuntimeAvailable, resolveChatNavVisible, shouldRedirectFromUnavailableChat } from './chat-availability'

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

describe('chat-availability', () => {
  it('reads runtime availability from backend status fields', () => {
    expect(isChatRuntimeAvailable(availableStatus)).toBe(true)
    expect(isChatRuntimeAvailable(disabledStatus)).toBe(false)
    expect(isChatRuntimeAvailable(undefined)).toBe(false)
  })

  it('falls back to bootstrap hint until status resolves', () => {
    expect(
      resolveChatNavVisible({
        hasOperationalAccess: true,
        status: undefined,
        statusResolved: false,
        bootstrapChatAvailable: true,
      }),
    ).toBe(true)

    expect(
      resolveChatNavVisible({
        hasOperationalAccess: true,
        status: disabledStatus,
        statusResolved: false,
        bootstrapChatAvailable: true,
      }),
    ).toBe(true)
  })

  it('uses runtime status once resolved', () => {
    expect(
      resolveChatNavVisible({
        hasOperationalAccess: true,
        status: availableStatus,
        statusResolved: true,
        bootstrapChatAvailable: false,
      }),
    ).toBe(true)

    expect(
      resolveChatNavVisible({
        hasOperationalAccess: true,
        status: disabledStatus,
        statusResolved: true,
        bootstrapChatAvailable: true,
      }),
    ).toBe(false)
  })

  it('hides chat nav without operational access', () => {
    expect(
      resolveChatNavVisible({
        hasOperationalAccess: false,
        status: availableStatus,
        statusResolved: true,
        bootstrapChatAvailable: true,
      }),
    ).toBe(false)
  })
})

describe('shouldRedirectFromUnavailableChat', () => {
  it('redirects only on resolved unavailable chat routes', () => {
    expect(
      shouldRedirectFromUnavailableChat({
        isChatRoute: true,
        statusResolved: true,
        isRuntimeAvailable: false,
      }),
    ).toBe(true)

    expect(
      shouldRedirectFromUnavailableChat({
        isChatRoute: false,
        statusResolved: true,
        isRuntimeAvailable: false,
      }),
    ).toBe(false)

    expect(
      shouldRedirectFromUnavailableChat({
        isChatRoute: true,
        statusResolved: false,
        isRuntimeAvailable: false,
      }),
    ).toBe(false)

    expect(
      shouldRedirectFromUnavailableChat({
        isChatRoute: true,
        statusResolved: true,
        isRuntimeAvailable: true,
      }),
    ).toBe(false)
  })
})
