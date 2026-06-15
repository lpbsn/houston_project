// @vitest-environment jsdom

import { createRef } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CommentComposer, type CommentComposerHandle } from './components/comment-composer'
import { stripFirstMentionText } from './components/selected-mention-chips'

vi.mock('./hooks', () => ({
  useMentionUserSearchQuery: () => ({
    data: [
      {
        membership_id: 'member-1',
        display_name: 'Marie Martin',
        role: 'staff',
        id: 'user-1',
        username: 'marie',
        email: 'marie@example.com',
      },
    ],
    isFetching: false,
  }),
}))

afterEach(() => {
  cleanup()
})

describe('stripFirstMentionText', () => {
  it('removes the first exact @DisplayName occurrence with trailing space', () => {
    expect(stripFirstMentionText('ping @Marie Martin suite', 'Marie Martin')).toBe('ping suite')
  })
})

describe('CommentComposer', () => {
  it('shows a removable mention chip and omits removed ids from submit payload', () => {
    const onSubmit = vi.fn()

    render(<CommentComposer establishmentId="est-1" onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText('Ajouter un commentaire')
    fireEvent.change(textarea, { target: { value: 'ping @ma', selectionStart: 8 } })
    fireEvent.click(screen.getByRole('button', { name: /Marie Martin/i }))

    expect(screen.getByLabelText('Mentions sélectionnées')).toBeTruthy()
    expect(screen.getByText('@Marie Martin')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Retirer la mention Marie Martin/i }))
    expect(screen.queryByLabelText('Mentions sélectionnées')).toBeNull()

    fireEvent.change(textarea, { target: { value: 'ping @ma', selectionStart: 8 } })
    fireEvent.click(screen.getByRole('button', { name: /Marie Martin/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Publier le commentaire' }))

    expect(onSubmit).toHaveBeenCalledWith({
      body: 'ping @Marie Martin',
      mentionedMembershipIds: ['member-1'],
    })
  })

  it('clears draft only when reset is called explicitly', () => {
    const onSubmit = vi.fn()
    const composerRef = createRef<CommentComposerHandle>()

    render(<CommentComposer ref={composerRef} establishmentId="est-1" onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText('Ajouter un commentaire')
    fireEvent.change(textarea, { target: { value: 'hello', selectionStart: 5 } })
    fireEvent.click(screen.getByRole('button', { name: 'Publier le commentaire' }))

    expect(onSubmit).toHaveBeenCalledWith({
      body: 'hello',
      mentionedMembershipIds: [],
    })
    expect((textarea as HTMLTextAreaElement).value).toBe('hello')

    act(() => {
      composerRef.current?.reset()
    })
    expect(screen.getByLabelText('Ajouter un commentaire')).toHaveProperty('value', '')
  })
})
