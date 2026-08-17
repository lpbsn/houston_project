// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createBrowserHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import type { AnalyticsSignalReturnContext } from '@/features/analytics/lib/analytics-url-state'

import type { SignalDetail } from '../types'

import { SignalDetailPage } from './signal-detail-page'

const navigate = vi.fn()
const detailQueryMock = vi.fn()

const {
  CommentSectionMock,
  SignalQualifyRoutingSheetMock,
  closeQualifySheetMock,
  openForSignalMock,
  submitQualifySheetMock,
  useSignalQualifySheetMock,
} = vi.hoisted(() => ({
  CommentSectionMock: vi.fn(() => createElement('div', { 'data-testid': 'comment-section' })),
  SignalQualifyRoutingSheetMock: vi.fn(() =>
    createElement('div', { 'data-testid': 'qualify-routing-sheet' }),
  ),
  closeQualifySheetMock: vi.fn(),
  openForSignalMock: vi.fn(),
  submitQualifySheetMock: vi.fn(),
  useSignalQualifySheetMock: vi.fn(),
}))

function buildLinkedExecution(
  overrides: Partial<SignalDetail['linked_action_plan_executions'][number]> = {},
): SignalDetail['linked_action_plan_executions'][number] {
  return {
    id: 'exec-1',
    title: 'Plan fuite',
    status: 'in_progress',
    requires_validation: false,
    validated_at: null,
    pilot_business_unit: { id: 'bu-1', specific_name: 'Maintenance', instance_description: '', active: true, generic: { key: 'maintenance', label: 'Maintenance', description: '', unit_type: 'dedicated' } },
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
    routing_status: 'resolved',
    issue_focus: '',
    is_pinned: false,
    affected_business_unit_id: 'bu-aff',
    affected_business_unit_key: 'restaurant',
    affected_business_unit_label: 'Restaurant',
    responsible_business_unit_id: 'bu-resp',
    responsible_business_unit_key: 'maintenance',
    responsible_business_unit_label: 'Maintenance',
    activity_subject_id: 'sub-1',
    activity_subject_normalized_name: 'electricite',
    activity_subject_label: 'Électricité',
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
    resolution_request: null,
    resolution_request_events: [],
    marked_interesting_by_membership_id: null,
    marked_interesting_at: null,
    resolved_by_membership_id: null,
    resolved_at: null,
    resolution_origin: null,
    canceled_by_membership_id: null,
    canceled_at: null,
    archived_by_membership_id: null,
    archived_at: null,
    permission_hints: {
      can_pin: false,
      can_mark_interesting: false,
      can_archive: false,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
      can_request_resolution: false,
      can_approve_resolution_request: false,
      can_reject_resolution_request: false,
      can_cancel_resolution_request: false,
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
  useCreateSignalResolutionRequestMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useApproveSignalResolutionRequestMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useRejectSignalResolutionRequestMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useCancelSignalResolutionRequestMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}))

vi.mock('@/features/comments/components/comment-section', () => ({
  CommentSection: CommentSectionMock,
}))

vi.mock('../hooks/use-signal-qualify-sheet', () => ({
  useSignalQualifySheet: useSignalQualifySheetMock,
}))

vi.mock('../components/signal-qualify-routing-sheet', () => ({
  SignalQualifyRoutingSheet: SignalQualifyRoutingSheetMock,
}))

function renderPage(options: { analyticsSignalReturnContext?: AnalyticsSignalReturnContext | null } = {}) {
  const history = createBrowserHistory()
  return render(
    createElement(
      AppRouteProvider,
      { history },
      createElement(SignalDetailPage, {
        signalId: 'signal-1',
        onNavigate: navigate,
        analyticsSignalReturnContext: options.analyticsSignalReturnContext,
      }),
    ),
  )
}

function getDetailsTab() {
  return screen.getByRole('tab', { name: 'Détails' })
}

function getCommentsTab() {
  return screen.getByRole('tab', { name: 'Commentaires' })
}

beforeEach(() => {
  openForSignalMock.mockResolvedValue({ ok: true })
  useSignalQualifySheetMock.mockReturnValue({
    open: false,
    opening: false,
    signalId: null,
    signal: null,
    isPending: false,
    errorMessage: null,
    openForSignal: openForSignalMock,
    close: closeQualifySheetMock,
    submit: submitQualifySheetMock,
  })
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
    expect(screen.getByText(/Rapportée par Marie R\./)).toBeTruthy()
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
    expect(screen.getByText(/Rapportée par Marie R\./)).toBeTruthy()
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
    expect(screen.getByText(/Rapportée par Marie R\./)).toBeTruthy()
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

  it('renders one responsive details layout without duplicate fetches or actions', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: true,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    const detailsPanel = screen.getByTestId('signal-detail-details-panel')
    expect(detailsPanel.className).toContain('lg:grid')
    expect(detailsPanel.className).toContain(
      'lg:grid-cols-[minmax(0,1fr)_minmax(18rem,24rem)]',
    )
    expect(detailsPanel.querySelector('.lg\\:row-start-2')).toBeNull()
    expect(screen.getAllByRole('button', { name: "+ Plan d'action" })).toHaveLength(1)
    expect(detailQueryMock).toHaveBeenCalledTimes(1)
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

  it('shows one create plan action only on Détails tab', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: true,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getAllByRole('button', { name: "+ Plan d'action" })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: "+ Plan d'action" }))
    expect(navigate).toHaveBeenCalledWith('/signals/signal-1/plan')

    fireEvent.click(getCommentsTab())

    expect(screen.queryByRole('button', { name: "+ Plan d'action" })).toBeNull()
  })

  it('preserves Analytics context when opening Signal-linked Plan creation', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: true,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage({
      analyticsSignalReturnContext: {
        patternId: '44444444-4444-4444-8444-444444444444',
        state: {
          periodStart: '2026-07-01T00:00:00.000Z',
          periodEnd: '2026-08-01T00:00:00.000Z',
          organizationId: null,
          establishmentIds: [],
          q: 'retard',
          recurrence: 'recurrent',
          responsibleBusinessUnitIds: [],
          responsibleBusinessUnitUnassigned: false,
          signalStatuses: [],
        },
      },
    })

    fireEvent.click(screen.getByRole('button', { name: "+ Plan d'action" }))

    expect(navigate).toHaveBeenCalledWith(
      '/signals/signal-1/plan?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent&analytics_pattern_id=44444444-4444-4444-8444-444444444444',
    )
  })

  it('wires qualify CTA to the qualification hook from detail', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        routing_status: 'unassigned',
        affected_business_unit_id: null,
        responsible_business_unit_id: null,
        activity_subject_id: null,
        affected_business_unit_key: null,
        affected_business_unit_label: null,
        responsible_business_unit_key: null,
        responsible_business_unit_label: null,
        activity_subject_normalized_name: null,
        activity_subject_label: null,
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: true,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Qualifier' }))

    expect(useSignalQualifySheetMock).toHaveBeenCalledWith({
      establishmentId: 'est-1',
      onNavigate: navigate,
    })
    expect(openForSignalMock).toHaveBeenCalledWith('signal-1')
    expect(screen.queryByText('À qualifier')).toBeNull()
    expect(screen.getByText('Non classifié')).toBeTruthy()
  })

  it('renders qualification sheet from qualify hook state', () => {
    const signal = buildSignal()
    useSignalQualifySheetMock.mockReturnValue({
      open: true,
      opening: false,
      signalId: signal.id,
      signal,
      isPending: true,
      errorMessage: 'Erreur de qualification.',
      openForSignal: openForSignalMock,
      close: closeQualifySheetMock,
      submit: submitQualifySheetMock,
    })

    renderPage()

    expect(screen.getByTestId('qualify-routing-sheet')).toBeTruthy()
    expect(SignalQualifyRoutingSheetMock).toHaveBeenCalledWith(
      expect.objectContaining({
        open: true,
        establishmentId: 'est-1',
        signal,
        isPending: true,
        errorMessage: 'Erreur de qualification.',
        onClose: closeQualifySheetMock,
      }),
      undefined,
    )
  })

  it('shows affected pole and Non classifié when only affected is set', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        routing_status: 'unassigned',
        affected_business_unit_id: 'bu-aff',
        affected_business_unit_key: 'communication',
        affected_business_unit_label: 'Communication',
        responsible_business_unit_id: null,
        responsible_business_unit_key: null,
        responsible_business_unit_label: null,
        activity_subject_id: null,
        activity_subject_normalized_name: null,
        activity_subject_label: null,
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText('Pôle concerné')).toBeTruthy()
    expect(screen.getByText('Communication')).toBeTruthy()
    expect(screen.getByText('Non classifié')).toBeTruthy()
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
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: true,
          can_resolve: true,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.queryByRole('button', { name: 'Résolu' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Annuler' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Marquer comme résolue' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Annuler cette observation' })).toBeNull()
  })

  it('shows create resolution request CTA when enabled', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: true,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText('Demande de résolution')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Demander la résolution' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Demander la résolution' }).className).toContain(
      'bg-[#114660]',
    )
  })

  it('places resolution section after description', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: true,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    const description = screen.getByText('Description')
    const resolution = screen.getByText('Demande de résolution')
    expect(
      description.compareDocumentPosition(resolution) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('shows pending history and requester cancel action', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        resolution_request: {
          id: 'req-1',
          status: 'pending',
          review_route: 'manager_to_director',
          requested_at: '2026-06-30T08:00:00Z',
          request_comment: 'Corrigé',
          reviewed_at: null,
          review_comment: '',
          canceled_at: null,
          canceled_reason: '',
          cancel_comment: '',
          requested_by_membership_id: 'membership-1',
          reviewed_by_membership_id: null,
        },
        resolution_request_events: [
          {
            request_id: 'req-1',
            event_type: 'created',
            occurred_at: '2026-06-30T08:00:00Z',
            actor_display_name: 'Alice',
          },
        ],
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: true,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(
      screen.getByText(/Demande de résolution en attente — Envoyée par Alice/),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Annuler la demande' })).toBeTruthy()
  })

  it('shows create+approve history and approve/reject actions', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        resolution_request: {
          id: 'req-1',
          status: 'pending',
          review_route: 'staff_to_manager',
          requested_at: '2026-06-30T08:00:00Z',
          request_comment: '',
          reviewed_at: null,
          review_comment: '',
          canceled_at: null,
          canceled_reason: '',
          cancel_comment: '',
          requested_by_membership_id: 'membership-1',
          reviewed_by_membership_id: null,
        },
        resolution_request_events: [
          {
            request_id: 'req-1',
            event_type: 'created',
            occurred_at: '2026-06-30T08:00:00Z',
            actor_display_name: 'Alice',
          },
        ],
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: true,
          can_reject_resolution_request: true,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    const approve = screen.getByRole('button', { name: 'Approuver' })
    const reject = screen.getByRole('button', { name: 'Refuser la demande' })
    expect(approve.className).toContain('bg-[#1D9E75]')
    expect(reject.className).toContain('bg-destructive')
  })

  it('keeps history and create CTA after rejected request', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        resolution_request: null,
        resolution_request_events: [
          {
            request_id: 'req-1',
            event_type: 'rejected',
            occurred_at: '2026-06-30T09:00:00Z',
            actor_display_name: 'Bob',
          },
          {
            request_id: 'req-1',
            event_type: 'created',
            occurred_at: '2026-06-30T08:00:00Z',
            actor_display_name: 'Alice',
          },
        ],
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: true,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText(/Demande de résolution refusée — Refusée par Bob/)).toBeTruthy()
    expect(screen.getByText(/Demande de résolution en attente — Envoyée par Alice/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Demander la résolution' })).toBeTruthy()
  })

  it('keeps history and create CTA after canceled request', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        resolution_request: null,
        resolution_request_events: [
          {
            request_id: 'req-1',
            event_type: 'canceled',
            occurred_at: '2026-06-30T09:00:00Z',
            actor_display_name: 'Alice',
          },
          {
            request_id: 'req-1',
            event_type: 'created',
            occurred_at: '2026-06-30T08:00:00Z',
            actor_display_name: 'Alice',
          },
        ],
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: true,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText(/Demande de résolution annulée — Annulée par Alice/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Demander la résolution' })).toBeTruthy()
  })

  it('renders reject then new request history in descending order', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        resolution_request: {
          id: 'req-2',
          status: 'pending',
          review_route: 'manager_to_director',
          requested_at: '2026-06-30T12:00:00Z',
          request_comment: '',
          reviewed_at: null,
          review_comment: '',
          canceled_at: null,
          canceled_reason: '',
          cancel_comment: '',
          requested_by_membership_id: 'membership-1',
          reviewed_by_membership_id: null,
        },
        resolution_request_events: [
          {
            request_id: 'req-2',
            event_type: 'created',
            occurred_at: '2026-06-30T12:00:00Z',
            actor_display_name: 'Alice',
          },
          {
            request_id: 'req-1',
            event_type: 'rejected',
            occurred_at: '2026-06-30T11:00:00Z',
            actor_display_name: 'Bob',
          },
          {
            request_id: 'req-1',
            event_type: 'created',
            occurred_at: '2026-06-30T10:00:00Z',
            actor_display_name: 'Alice',
          },
        ],
        permission_hints: {
          can_pin: false,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: true,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    const items = screen.getAllByRole('listitem').map((item) => item.textContent ?? '')
    expect(items).toHaveLength(3)
    expect(items[0]).toContain('Envoyée par Alice')
    expect(items[1]).toContain('Refusée par Bob')
    expect(items[2]).toContain('Envoyée par Alice')
  })
})

describe('SignalDetailPage pin actions', () => {
  it('does not show pin actions on details tab', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({
        permission_hints: {
          can_pin: true,
          can_mark_interesting: false,
          can_archive: false,
          can_cancel: false,
          can_resolve: false,
          can_create_linked_action_plan: false,
          can_qualify_routing: false,
          can_request_resolution: false,
          can_approve_resolution_request: false,
          can_reject_resolution_request: false,
          can_cancel_resolution_request: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.queryByRole('button', { name: 'Épingler' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Désépingler' })).toBeNull()
  })
})

describe('SignalDetailPage linked action plans', () => {
  it('does not show Plans d action section when list is empty', () => {
    renderPage()

    expect(screen.queryByText("Plans d'action")).toBeNull()
  })

  it('shows resolve-via-action-plan hint when status is in_progress', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignal({ status: 'in_progress' }),
      refetch: vi.fn(),
    })

    renderPage()

    expect(
      screen.getByText('Cette observation sera résolue via son plan d’action.'),
    ).toBeTruthy()
  })

  it('does not show resolve-via-action-plan hint when status is open', () => {
    renderPage()

    expect(
      screen.queryByText('Cette observation sera résolue via son plan d’action.'),
    ).toBeNull()
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
