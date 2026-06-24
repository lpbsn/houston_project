// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { buildActionFeedItem } from '@/features/actions/test-fixtures'

import { ExecutionActionCard } from './execution-action-card'

afterEach(() => {
  cleanup()
})

describe('ExecutionActionCard classic footer', () => {
  it('shows accepted_by executor on in-progress actions', () => {
    render(
      createElement(ExecutionActionCard, {
        item: buildActionFeedItem({
          status: 'in_progress',
          created_by_display_name: 'Creator',
          assignees: [
            {
              membership_id: 'member-assignee',
              display_name: 'Assignee',
              role: 'staff',
            },
          ],
          accepted_by: {
            membership_id: 'member-executor',
            display_name: 'Jean Dupont',
          },
        }),
        onSelect: vi.fn(),
      }),
    )

    expect(screen.getByText('En cours · Jean D.')).toBeTruthy()
    expect(screen.queryByText(/Créé par/)).toBeNull()
  })

  it('shows assignees when action is open and not yet accepted', () => {
    render(
      createElement(ExecutionActionCard, {
        item: buildActionFeedItem({
          status: 'open',
          created_by_display_name: 'Creator',
          assignees: [
            {
              membership_id: 'member-a',
              display_name: 'Alice Martin',
              role: 'staff',
            },
            {
              membership_id: 'member-b',
              display_name: 'Bob Martin',
              role: 'staff',
            },
          ],
          accepted_by: null,
        }),
        onSelect: vi.fn(),
      }),
    )

    expect(screen.getByText('Alice M., Bob M.')).toBeTruthy()
    expect(screen.queryByText(/Créé par/)).toBeNull()
  })

  it('falls back to creator when no assignees are present', () => {
    render(
      createElement(ExecutionActionCard, {
        item: buildActionFeedItem({
          status: 'open',
          created_by_display_name: 'Creator Person',
          assignees: [],
          accepted_by: null,
        }),
        onSelect: vi.fn(),
      }),
    )

    expect(screen.getByText('Créé par Creator P.')).toBeTruthy()
  })
})
