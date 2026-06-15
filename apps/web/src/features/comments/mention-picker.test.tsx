// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { getActiveMentionQuery, MentionPicker } from './components/mention-picker'

describe('getActiveMentionQuery', () => {
  it('returns null when no mention trigger is active', () => {
    expect(getActiveMentionQuery('hello world', 5)).toBeNull()
  })

  it('returns query after @ when at least two characters are typed', () => {
    expect(getActiveMentionQuery('ping @ma', 8)).toBe('ma')
  })

  it('returns null when mention fragment contains whitespace', () => {
    expect(getActiveMentionQuery('ping @ma ri', 10)).toBeNull()
  })
})

describe('MentionPicker', () => {
  it('renders tap-friendly suggestions and calls onSelect', () => {
    const onSelect = vi.fn()

    render(
      <MentionPicker
        results={[
          {
            membership_id: 'member-1',
            display_name: 'Marie Martin',
            role: 'staff',
            id: 'user-1',
            username: 'marie',
            email: 'marie@example.com',
          },
        ]}
        isLoading={false}
        query="mar"
        selectedMembershipIds={[]}
        onSelect={onSelect}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Marie Martin/i }))
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ membership_id: 'member-1' }),
    )
  })

  it('shows minimum length hint before two characters', () => {
    render(
      <MentionPicker
        results={[]}
        isLoading={false}
        query="m"
        selectedMembershipIds={[]}
        onSelect={vi.fn()}
      />,
    )

    expect(screen.getByText(/au moins 2 caractères/i)).toBeTruthy()
  })
})
