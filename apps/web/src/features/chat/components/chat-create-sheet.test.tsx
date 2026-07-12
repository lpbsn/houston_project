// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ChatCreateSheet } from './chat-create-sheet'

vi.mock('../hooks', () => ({
  useEligibleChatMembershipsQuery: () => ({
    isLoading: false,
    isError: false,
    data: { items: [] },
  }),
  useCreateDmMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
    reset: vi.fn(),
  }),
  useCreateGroupMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
    reset: vi.fn(),
  }),
}))

function renderSheet() {
  return render(
    createElement(ChatCreateSheet, {
      establishmentId: 'est-1',
      open: true,
      canCreateDm: true,
      canCreateGroup: true,
      onClose: () => undefined,
      onConversationCreated: () => undefined,
    }),
  )
}

describe('ChatCreateSheet menu icons', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders the expected icon in each menu button', () => {
    renderSheet()

    const dmButton = screen.getByRole('button', { name: 'Message direct' })
    const groupButton = screen.getByRole('button', { name: 'Groupe' })

    expect(dmButton.querySelector('.lucide-user')).toBeTruthy()
    expect(groupButton.querySelector('.lucide-users')).toBeTruthy()
  })
})
