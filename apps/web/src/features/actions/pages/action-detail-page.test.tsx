// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionDetail } from '@/features/actions/types'

import { ActionDetailPage } from './action-detail-page'

const navigate = vi.fn()
const acceptMutate = vi.fn()
const detailQueryMock = vi.fn()

const { CommentSectionMock } = vi.hoisted(() => ({
  CommentSectionMock: vi.fn(() => createElement('div', { 'data-testid': 'comment-section' })),
}))

function buildAction(overrides: Partial<ActionDetail> = {}): ActionDetail {
  return {
    id: 'action-1',
    title: 'Nettoyer la terrasse',
    instruction_short: 'Nettoyer',
    status: 'open',
    due_at: '2026-06-30T18:00:00Z',
    is_overdue: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    signal_summary: null,
    assignees: [],
    accepted_by: null,
    requires_validation: false,
    created_by_display_name: 'Alice',
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    permission_hints: {
      can_accept: true,
      can_mark_done: false,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_reassign: false,
      can_update_due_at: false,
      is_assignee: false,
      accepted_by_me: false,
    },
    instruction: 'Passer la serpillière sur toute la terrasse.',
    accepted_at: null,
    marked_done_at: null,
    validated_at: null,
    ...overrides,
  }
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        establishment_id: 'est-1',
        id: 'membership-1',
      },
    },
  }),
}))

vi.mock('../hooks', () => ({
  useActionDetailQuery: () => detailQueryMock(),
  useAcceptActionMutation: () => ({
    mutate: acceptMutate,
    isPending: false,
    error: null,
  }),
  useMarkActionDoneMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    error: null,
  }),
  useValidateActionMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    error: null,
  }),
  useReopenActionMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    error: null,
  }),
  useCancelActionMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    error: null,
  }),
}))

vi.mock('@/features/comments/components/comment-section', () => ({
  CommentSection: CommentSectionMock,
}))

function renderPage() {
  return render(
    createElement(ActionDetailPage, {
      actionId: 'action-1',
      onNavigate: navigate,
    }),
  )
}

function getDetailsTab() {
  return screen.getByRole('button', { name: 'Détails' })
}

function getCommentsTab() {
  return screen.getByRole('button', { name: 'Commentaires' })
}

function getDetailsPanel() {
  let element: HTMLElement | null = screen.getByText('Nettoyer la terrasse')
  while (element) {
    if (element.classList.contains('flex-col')) {
      return element
    }
    element = element.parentElement
  }
  return null
}

function getCommentsPanel() {
  return screen.getByTestId('comment-section').parentElement
}

function isPanelHidden(panel: HTMLElement | null | undefined) {
  return panel?.classList.contains('hidden') ?? false
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ActionDetailPage tabs', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildAction(),
      error: null,
      refetch: vi.fn(),
    })
  })

  it('shows Détails tab as active by default', () => {
    renderPage()

    expect(getDetailsTab().getAttribute('aria-pressed')).toBe('true')
    expect(getCommentsTab().getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Nettoyer la terrasse')).toBeTruthy()
  })

  it('does not mount CommentSection on first render', () => {
    renderPage()

    expect(screen.queryByTestId('comment-section')).toBeNull()
    expect(CommentSectionMock).not.toHaveBeenCalled()
  })

  it('mounts CommentSection on first click on Commentaires', () => {
    renderPage()

    fireEvent.click(getCommentsTab())

    expect(screen.getByTestId('comment-section')).toBeTruthy()
    expect(CommentSectionMock).toHaveBeenCalled()
    expect(isPanelHidden(getDetailsPanel())).toBe(true)
  })

  it('hides comments panel when returning to Détails but keeps CommentSection mounted', () => {
    renderPage()

    fireEvent.click(getCommentsTab())
    const commentSection = screen.getByTestId('comment-section')

    fireEvent.click(getDetailsTab())

    expect(commentSection).toBeTruthy()
    expect(isPanelHidden(getCommentsPanel())).toBe(true)
    expect(isPanelHidden(getDetailsPanel())).toBe(false)
  })

  it('shows comments panel again without remounting CommentSection', () => {
    renderPage()

    fireEvent.click(getCommentsTab())
    const commentSection = screen.getByTestId('comment-section')

    fireEvent.click(getDetailsTab())
    fireEvent.click(getCommentsTab())

    expect(screen.getByTestId('comment-section')).toBe(commentSection)
    expect(isPanelHidden(getCommentsPanel())).toBe(false)
  })

  it('shows sticky footer only on Détails tab', () => {
    renderPage()

    expect(screen.getByRole('button', { name: 'Accepter' })).toBeTruthy()

    fireEvent.click(getCommentsTab())

    expect(screen.queryByRole('button', { name: 'Accepter' })).toBeNull()

    fireEvent.click(getDetailsTab())

    expect(screen.getByRole('button', { name: 'Accepter' })).toBeTruthy()
  })

  it('still triggers accept mutation from Détails tab', () => {
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Accepter' }))

    expect(acceptMutate).toHaveBeenCalledTimes(1)
  })
})
