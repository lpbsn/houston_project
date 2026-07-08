// @vitest-environment jsdom

import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  MENTION_DEEP_LINK_BADGE_DURATION_MS,
  MentionDeepLinkBadge,
  useMentionDeepLinkBadge,
} from './mention-deep-link-badge'

function BadgeProbe({
  commentId,
  highlightCommentId,
}: {
  commentId: string
  highlightCommentId?: string | null
}) {
  const showBadge = useMentionDeepLinkBadge(commentId, highlightCommentId)

  return <div>{showBadge ? <MentionDeepLinkBadge /> : null}</div>
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('MentionDeepLinkBadge', () => {
  it('renders an accessible mention badge', () => {
    render(<MentionDeepLinkBadge />)

    expect(
      screen.getByLabelText('Vous avez été mentionné dans ce commentaire'),
    ).toBeTruthy()
  })
})

describe('useMentionDeepLinkBadge', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('shows the badge when the comment matches the highlight id', () => {
    render(<BadgeProbe commentId="comment-1" highlightCommentId="comment-1" />)

    expect(
      screen.getByLabelText('Vous avez été mentionné dans ce commentaire'),
    ).toBeTruthy()
  })

  it('does not show the badge when ids do not match', () => {
    render(<BadgeProbe commentId="comment-1" highlightCommentId="comment-2" />)

    expect(
      screen.queryByLabelText('Vous avez été mentionné dans ce commentaire'),
    ).toBeNull()
  })

  it('hides the badge after the configured duration', async () => {
    render(<BadgeProbe commentId="comment-1" highlightCommentId="comment-1" />)

    expect(
      screen.getByLabelText('Vous avez été mentionné dans ce commentaire'),
    ).toBeTruthy()

    vi.advanceTimersByTime(MENTION_DEEP_LINK_BADGE_DURATION_MS)

    await act(async () => {})

    expect(
      screen.queryByLabelText('Vous avez été mentionné dans ce commentaire'),
    ).toBeNull()
  })
})
