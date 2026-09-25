import { describe, expect, it } from 'vitest'

import type { AppRoute } from '@/app/app-routes'

import {
  desktopChatMountKey,
  resolveDesktopChatPageProps,
} from './chat-desktop-surface'

describe('resolveDesktopChatPageProps', () => {
  it('returns null outside desktop web', () => {
    expect(
      resolveDesktopChatPageProps({ kind: 'static', path: '/chat' }, false, 'est-1'),
    ).toBeNull()
  })

  it('unifies /chat, scoped establishment chat, and /chat/:id with an effective establishment', () => {
    expect(resolveDesktopChatPageProps({ kind: 'static', path: '/chat' }, true, 'est-1')).toEqual({
      establishmentId: 'est-1',
      selectedConversationId: null,
    })
    expect(
      resolveDesktopChatPageProps(
        {
          kind: 'scoped-terrain',
          scope: { type: 'establishment', establishmentId: 'est-scoped' },
          page: 'chat',
        },
        true,
        'est-1',
      ),
    ).toEqual({
      establishmentId: 'est-scoped',
      selectedConversationId: null,
    })
    expect(
      resolveDesktopChatPageProps(
        { kind: 'chat-conversation-detail', conversationId: 'conv-a' },
        true,
        'est-1',
      ),
    ).toEqual({
      establishmentId: 'est-1',
      selectedConversationId: 'conv-a',
    })
  })

  it('excludes Cross chat', () => {
    const route: AppRoute = {
      kind: 'scoped-terrain',
      scope: { type: 'cross' },
      page: 'chat',
    }
    expect(resolveDesktopChatPageProps(route, true, 'est-1')).toBeNull()
  })
})

describe('desktopChatMountKey', () => {
  it('is stable for the same establishment and changes when the establishment changes', () => {
    expect(desktopChatMountKey('est-a')).toBe('chat:est-a')
    expect(desktopChatMountKey('est-a')).toBe(desktopChatMountKey('est-a'))
    expect(desktopChatMountKey('est-a')).not.toBe(desktopChatMountKey('est-b'))
    expect(desktopChatMountKey(null)).toBe('chat:none')
  })
})
