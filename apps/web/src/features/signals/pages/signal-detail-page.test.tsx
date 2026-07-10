// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignalDetail } from '../types'

import { SignalDetailPage } from './signal-detail-page'

const navigate = vi.fn()
const detailQueryMock = vi.fn()

const { CommentSectionMock } = vi.hoisted(() => ({
  CommentSectionMock: vi.fn(() => createElement('div', { 'data-testid': 'comment-section' })),
}))

function buildLinkedExecution(
  overrides: Partial<SignalDetail['linked_action_plan_executions'][number]> = {},
): SignalDetail['linked_action_plan_executions'][number] {
  return {
    id: 'exec-1',
    title: 'Plan fuite',
    status: 'in_progress',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', key: 'maintenance', label: 'Maintenance' },
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    ...overrides,
  }
}

function buildSignal(overrides: Partial<SignalDetail> = {}): SignalDetail {
  return {
    id: 'signal-1',
    title: 'Fuite d eau',
    structured_summary_short: 'Short',
    structured_summary: 'Description du signal.',
    status: 'open',
    urgency: 'normal',
    is_pinned: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    reporter_display_name: 'Marie R.',
    source_context: {
      submitted_at: '2026-06-30T08:00:00Z',
      reporter_display_name: 'Marie R.',
      media_count: 0,
    },
    media_items: [],
    linked_action_plan_executions: [],
    permission_hints: {
      can_pin: false,
      can_set_urgency: false,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
    },
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
  useSignalDetailQuery: () => detailQueryMock(),
}))

vi.mock('@/features/comments/components/comment-section', () => ({
  CommentSection: CommentSectionMock,
}))

function renderPage() {
  return render(
    createElement(SignalDetailPage, {
      signalId: 'signal-1',
      onNavigate: navigate,
    }),
  )
}

function getDetailsTab() {
  return screen.getByRole('tab', { name: 'Détails' })
}

function getCommentsTab() {
  return screen.getByRole('tab', { name: 'Commentaires' })
}

beforeEach(() => {
  detailQueryMock.mockReturnValue({
    isLoading: false,
    isError: false,
    data: buildSignal(),
    refetch: vi.fn(),
  })
})

afterEach(() => {
  window.history.replaceState(null, '', '/')
  cleanup()
  vi.clearAllMocks()
})

describe('SignalDetailPage aggregation count', () => {
  it('does not show aggregation label when aggregation_count is zero', () => {
    renderPage()

    expect(screen.queryByText(/agrégation/i)).toBeNull()
    expect(screen.getByText(/Signalé par Marie R\./)).toBeTruthy()
  })

  it('shows singular aggregation label on reporter line', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({ aggregation_count: 1 }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText('1 agrégation')).toBeTruthy()
    expect(screen.getByText(/Signalé par Marie R\./)).toBeTruthy()
  })

  it('shows plural aggregation label on reporter line', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({ aggregation_count: 3 }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText('3 agrégations')).toBeTruthy()
    expect(screen.getByText(/Signalé par Marie R\./)).toBeTruthy()
  })
})

describe('SignalDetailPage tabs', () => {
  it('shows Détails tab by default and does not mount CommentSection', () => {
    renderPage()

    expect(getDetailsTab().getAttribute('aria-selected')).toBe('true')
    expect(getCommentsTab().getAttribute('aria-selected')).toBe('false')
    expect(screen.getByText('Fuite d eau')).toBeTruthy()
    expect(screen.queryByTestId('comment-section')).toBeNull()
    expect(CommentSectionMock).not.toHaveBeenCalled()
  })

  it('mounts CommentSection on first click on Commentaires', () => {
    renderPage()

    fireEvent.click(getCommentsTab())

    expect(screen.getByTestId('comment-section')).toBeTruthy()
    expect(CommentSectionMock).toHaveBeenCalledWith(
      expect.objectContaining({
        establishmentId: 'est-1',
        targetType: 'signal',
        targetId: 'signal-1',
        highlightCommentId: null,
      }),
      undefined,
    )
  })

  it('opens comments tab and passes highlight id from deep link query params', () => {
    window.history.replaceState(
      null,
      '',
      '/signals/signal-1?tab=comments&commentId=comment-42',
    )

    renderPage()

    expect(getCommentsTab().getAttribute('aria-selected')).toBe('true')
    expect(screen.getByTestId('comment-section')).toBeTruthy()
    expect(CommentSectionMock).toHaveBeenCalledWith(
      expect.objectContaining({
        highlightCommentId: 'comment-42',
      }),
      undefined,
    )
  })

  it('shows sticky footer only on Détails tab', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_set_urgency: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: true,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByRole('button', { name: "+ Plan d'action" })).toBeTruthy()

    fireEvent.click(getCommentsTab())

    expect(screen.queryByRole('button', { name: "+ Plan d'action" })).toBeNull()
  })
})

describe('SignalDetailPage lifecycle actions', () => {
  it('does not show resolve or cancel actions on details tab', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_set_urgency: false,
          can_cancel: true,
          can_resolve: true,
          can_create_linked_action_plan: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.queryByRole('button', { name: 'Résolu' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Annuler' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Marquer résolu' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Annuler ce signal' })).toBeNull()
  })
})

describe('SignalDetailPage pin and urgency actions', () => {
  it('does not show pin or urgency actions on details tab', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: true,
          can_set_urgency: true,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.queryByRole('button', { name: 'Épingler' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Désépingler' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Marquer urgent' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Priorité normale' })).toBeNull()
  })
})

describe('SignalDetailPage linked action plans', () => {
  it('does not show Plans d action section when list is empty', () => {
    renderPage()

    expect(screen.queryByText("Plans d'action")).toBeNull()
  })

  it('shows linked execution card and navigates on click', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        linked_action_plan_executions: [buildLinkedExecution()],
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText("Plans d'action")).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Plan fuite/i }))

    expect(navigate).toHaveBeenCalledWith('/action-plans/executions/exec-1')
  })

  it('shows all linked executions', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        linked_action_plan_executions: [
          buildLinkedExecution({ id: 'exec-1', title: 'Plan A' }),
          buildLinkedExecution({ id: 'exec-2', title: 'Plan B' }),
        ],
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByRole('button', { name: /Plan A/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Plan B/i })).toBeTruthy()
  })
})
