// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChatConversationListItem } from '../types'

import { ChatPage } from './chat-page'

const statusQueryMock = vi.fn()
const conversationsQueryMock = vi.fn()

function buildConversation(
  id: string,
  type: 'dm' | 'group',
  options: {
    title?: string
    peerDisplayName?: string
  } = {},
): ChatConversationListItem {
  const peerDisplayName = options.peerDisplayName ?? 'Bob Martin'

  return {
    id,
    type,
    title: options.title ?? '',
    unread: false,
    last_message_at: '2026-06-13T12:00:00Z',
    last_message_preview: null,
    participants:
      type === 'dm'
        ? [
            {
              membership_id: 'mbr-viewer',
              user_id: 'user-viewer',
              display_name: 'Alice',
              role: 'staff',
              participant_role: 'member',
            },
            {
              membership_id: `mbr-peer-${id}`,
              user_id: `user-peer-${id}`,
              display_name: peerDisplayName,
              role: 'manager',
              participant_role: 'member',
            },
          ]
        : [
            {
              membership_id: 'mbr-viewer',
              user_id: 'user-viewer',
              display_name: 'Alice',
              role: 'staff',
              participant_role: 'member',
            },
            {
              membership_id: `mbr-member-${id}`,
              user_id: `user-member-${id}`,
              display_name: 'Claire Dupont',
              role: 'staff',
              participant_role: 'member',
            },
          ],
  }
}

function buildStatusQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    data: {
      can_access: true,
      chat_enabled: true,
      can_create_dm: true,
      can_create_group: true,
      can_manage_settings: false,
    },
    ...overrides,
  }
}

function buildConversationsQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: { items: [] as ChatConversationListItem[] },
    ...overrides,
  }
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        id: 'mbr-viewer',
        establishment_id: 'est-1',
      },
      user: {
        username: 'viewer',
      },
    },
  }),
}))

vi.mock('../hooks', () => ({
  useChatStatusQuery: () => statusQueryMock(),
  useChatConversationsQuery: () => conversationsQueryMock(),
  useEligibleChatMembershipsQuery: () => ({
    isLoading: false,
    isError: false,
    data: { items: [] },
  }),
  useCreateDmMutation: () => ({
    mutate: () => undefined,
    isPending: false,
  }),
  useCreateGroupMutation: () => ({
    mutate: () => undefined,
    isPending: false,
  }),
}))

function renderChatPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChatPage, {
        onOpenConversation: () => undefined,
      }),
    ),
  )
}

describe('ChatPage conversation sections', () => {
  beforeEach(() => {
    statusQueryMock.mockReturnValue(buildStatusQueryState())
    conversationsQueryMock.mockReturnValue(buildConversationsQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  it('renders direct and group sections for mixed conversations', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-dm', 'dm'),
            buildConversation('conv-group', 'group', { title: 'Équipe cuisine' }),
          ],
        },
      }),
    )

    renderChatPage()

    expect(screen.getByText('Messages directs')).toBeTruthy()
    expect(screen.getByText('Groupes')).toBeTruthy()
    expect(screen.getByText('Bob Martin')).toBeTruthy()
    expect(screen.getByText('Équipe cuisine')).toBeTruthy()
  })

  it('renders only the direct section when there are no groups', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [buildConversation('conv-dm', 'dm')],
        },
      }),
    )

    renderChatPage()

    expect(screen.getByText('Messages directs')).toBeTruthy()
    expect(screen.queryByText('Groupes')).toBeNull()
  })

  it('filters search results within the matching section', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-dm', 'dm', { peerDisplayName: 'Bob Martin' }),
            buildConversation('conv-group', 'group', { title: 'Équipe cuisine' }),
          ],
        },
      }),
    )

    renderChatPage()

    fireEvent.change(screen.getByPlaceholderText('Rechercher une conversation'), {
      target: { value: 'bob' },
    })

    expect(screen.getByText('Messages directs')).toBeTruthy()
    expect(screen.queryByText('Groupes')).toBeNull()
    expect(screen.getByText('Bob Martin')).toBeTruthy()
    expect(screen.queryByText('Équipe cuisine')).toBeNull()
  })

  it('shows search empty state when no conversation matches', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [buildConversation('conv-dm', 'dm')],
        },
      }),
    )

    renderChatPage()

    fireEvent.change(screen.getByPlaceholderText('Rechercher une conversation'), {
      target: { value: 'introuvable' },
    })

    expect(screen.getByText('Aucun résultat')).toBeTruthy()
    expect(screen.queryByText('Aucune conversation')).toBeNull()
  })

  it('shows global empty state when there are no conversations', () => {
    renderChatPage()

    expect(screen.getByText('Aucune conversation')).toBeTruthy()
    expect(screen.queryByText('Messages directs')).toBeNull()
    expect(screen.queryByText('Groupes')).toBeNull()
  })
})
