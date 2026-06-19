// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignalDetail } from '../types'

import { SignalDetailPage } from './signal-detail-page'

const navigate = vi.fn()
const detailQueryMock = vi.fn()

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
    permission_hints: {
      can_pin: false,
      can_set_urgency: false,
      can_cancel: false,
      can_resolve: false,
      can_create_action: false,
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
  usePinSignalMutation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useUnpinSignalMutation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useSignalUrgencyMutation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useCancelSignalMutation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useResolveSignalMutation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
}))

vi.mock('@/features/comments/components/comment-section', () => ({
  CommentSection: () => createElement('div', { 'data-testid': 'comment-section' }),
}))

function renderPage() {
  return render(
    createElement(SignalDetailPage, {
      signalId: 'signal-1',
      onNavigate: navigate,
    }),
  )
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
