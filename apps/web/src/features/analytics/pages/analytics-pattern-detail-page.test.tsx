// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  AnalyticsPatternDetailResponse,
  AnalyticsPatternSignalsResponse,
} from '@/features/analytics/api'
import { AnalyticsApiError } from '@/features/analytics/api'
import { AnalyticsPatternDetailPage } from '@/features/analytics/pages/analytics-pattern-detail-page'
import type { AnalyticsUrlState } from '@/features/analytics/lib/analytics-url-state'

const detailQueryMock = vi.fn()
const patternSignalsQueryMock = vi.fn()
const reportIssueMutationMock = vi.fn()
const governanceTargetsQueryMock = vi.fn()
const renameMutationMock = vi.fn()
const mergeMutationMock = vi.fn()
const moveMutationMock = vi.fn()
const splitExistingMutationMock = vi.fn()
const splitNewMutationMock = vi.fn()
const switchEstablishmentMock = vi.fn()

const { authState, notifySuccessMock, queryClientMock } = vi.hoisted(() => ({
  authState: {
    current: {
      bootstrap: null,
      isBootstrapping: false,
      isReady: true,
    },
  },
  notifySuccessMock: vi.fn(),
  queryClientMock: {
    invalidateQueries: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => queryClientMock,
}))

vi.mock('@/lib/success-toast', () => ({
  notifySuccess: notifySuccessMock,
}))

vi.mock('@/features/analytics/hooks', () => ({
  useAnalyticsPatternDetailQuery: (...args: unknown[]) => detailQueryMock(...args),
  useAnalyticsPatternSignalsInfiniteQuery: (...args: unknown[]) =>
    patternSignalsQueryMock(...args),
  useAnalyticsPatternGovernanceTargetsInfiniteQuery: (...args: unknown[]) =>
    governanceTargetsQueryMock(...args),
  useReportAnalyticsPatternIssueMutation: () => reportIssueMutationMock(),
  useRenameAnalyticsPatternMutation: () => renameMutationMock(),
  useMergeAnalyticsPatternsMutation: () => mergeMutationMock(),
  useMoveAnalyticsPatternSignalsMutation: () => moveMutationMock(),
  useSplitAnalyticsPatternToExistingMutation: () => splitExistingMutationMock(),
  useSplitAnalyticsPatternToNewMutation: () => splitNewMutationMock(),
}))

vi.mock('@/features/auth/api', () => ({
  switchEstablishment: (...args: unknown[]) => switchEstablishmentMock(...args),
}))

const analyticsState: AnalyticsUrlState = {
  periodStart: '2026-07-01T00:00:00.000Z',
  periodEnd: '2026-08-01T00:00:00.000Z',
  organizationId: '11111111-1111-4111-8111-111111111111',
  establishmentIds: ['22222222-2222-4222-8222-222222222222'],
  q: 'retard',
  recurrence: 'recurrent',
  responsibleBusinessUnitIds: ['33333333-3333-4333-8333-333333333333'],
  responsibleBusinessUnitUnassigned: true,
  signalStatuses: ['open'],
}

function bootstrap(
  role: string,
  options: { organizationId?: string; establishmentId?: string } = {},
) {
  const activeMembership = {
    id: `member-${role}`,
    establishment_id: options.establishmentId ?? 'est-1',
    establishment_name: 'Spore 1',
    organization_id: options.organizationId ?? '11111111-1111-4111-8111-111111111111',
    organization_name: 'Spore',
    role,
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }

  return {
    active_membership: activeMembership,
    memberships: [activeMembership],
  }
}

function detail(overrides: Partial<AnalyticsPatternDetailResponse> = {}): AnalyticsPatternDetailResponse {
  return {
    identity: {
      pattern_id: '44444444-4444-4444-8444-444444444444',
      label: 'Retard livraison',
      status: 'active',
      created_at: '2026-07-13T10:30:00.000Z',
      merged_into_pattern_id: null,
    },
    current_period: {
      period_start: '2026-07-01T00:00:00.000Z',
      period_end: '2026-08-01T00:00:00.000Z',
    },
    previous_period: {
      period_start: '2026-06-01T00:00:00.000Z',
      period_end: '2026-07-01T00:00:00.000Z',
    },
    metrics: {
      signal_count: 8,
      previous_signal_count: 5,
      signal_count_comparison: {
        current_value: 8,
        previous_value: 5,
        absolute_delta: 3,
        relative_change: 0.6,
        relative_change_status: 'computed',
      },
      actionable_signal_count: 2,
      last_seen_at: '2026-07-31T08:30:00.000Z',
      establishment_count: 2,
    },
    is_recurrent: true,
    occurrence_count_30d: 4,
    distinct_day_count_30d: 2,
    recurrence_window: {
      window_start: '2026-07-02T00:00:00.000Z',
      window_end: '2026-08-01T00:00:00.000Z',
    },
    recurrence_status: 'computed',
    trend_timezone: 'UTC',
    trend: [
      {
        bucket_date: '2026-07-31',
        bucket_start: '2026-07-31T00:00:00.000Z',
        bucket_end: '2026-08-01T00:00:00.000Z',
        signal_count: 8,
      },
    ],
    status_distribution: [{ status: 'open', signal_count: 8 }],
    establishments: [
      {
        establishment_id: 'est-1',
        name: 'Spore Marais',
        signal_count: 5,
      },
    ],
    establishment_bucket_count: 2,
    establishment_other_signal_count: 3,
    responsible_business_units: [
      {
        business_unit_id: null,
        name: 'Non assigné',
        signal_count: 2,
      },
    ],
    business_unit_bucket_count: 1,
    business_unit_other_signal_count: 0,
    drilldown_context: {
      pattern_id: '44444444-4444-4444-8444-444444444444',
      period_start: '2026-07-01T00:00:00.000Z',
      period_end: '2026-08-01T00:00:00.000Z',
      organization_id: '11111111-1111-4111-8111-111111111111',
      establishment_id: null,
    },
    ...overrides,
  }
}

function setDetailQuery(value: ReturnType<typeof detailQueryMock> = {}) {
  detailQueryMock.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...value,
  })
  setPatternSignalsQuery()
  setGovernanceTargetsQuery()
  setReportIssueMutation()
  setOwnerGovernanceMutations()
}

function signals(
  overrides: Partial<AnalyticsPatternSignalsResponse> = {},
): AnalyticsPatternSignalsResponse {
  return {
    period: {
      period_start: '2026-07-01T00:00:00.000Z',
      period_end: '2026-08-01T00:00:00.000Z',
    },
    items: [
      {
        signal_id: '55555555-5555-4555-8555-555555555555',
        title: 'Signal retard',
        structured_summary: 'Livraison arrivée en retard.',
        status: 'open',
        created_at: '2026-07-31T08:30:00.000Z',
        resolved_at: null,
        establishment: {
          id: 'est-1',
          name: 'Spore 1',
        },
        responsible_business_unit: {
          id: '33333333-3333-4333-8333-333333333333',
          specific_name: 'Cuisine',
        },
      },
    ],
    page_size: 25,
    has_more: false,
    next_cursor: null,
    ...overrides,
  }
}

function setPatternSignalsQuery(value: ReturnType<typeof patternSignalsQueryMock> = {}) {
  patternSignalsQueryMock.mockReturnValue({
    data: { pages: [signals()] },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
    ...value,
  })
}

function setGovernanceTargetsQuery(value: ReturnType<typeof governanceTargetsQueryMock> = {}) {
  governanceTargetsQueryMock.mockReturnValue({
    data: {
      pages: [
        {
          items: [
            {
              pattern_id: '77777777-7777-4777-8777-777777777777',
              label: 'Motif cible',
              normalized_label: 'motif cible',
              status: 'active',
              merged_into_pattern_id: null,
            },
          ],
          page_size: 20,
          has_more: false,
          next_cursor: null,
        },
      ],
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
    ...value,
  })
}

function setReportIssueMutation(value: ReturnType<typeof reportIssueMutationMock> = {}) {
  reportIssueMutationMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({ report_id: 'report-1' }),
    isPending: false,
    ...value,
  })
}

function setOwnerGovernanceMutations() {
  renameMutationMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Nouveau motif',
        normalized_label: 'nouveau motif',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: null,
      moved_signal_count: 0,
      target_created: false,
    }),
    isPending: false,
  })
  mergeMutationMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'merged',
        merged_into_pattern_id: '77777777-7777-4777-8777-777777777777',
      },
      target_pattern: {
        pattern_id: '77777777-7777-4777-8777-777777777777',
        label: 'Motif cible',
        normalized_label: 'motif cible',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 2,
      target_created: false,
    }),
    isPending: false,
  })
  moveMutationMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: {
        pattern_id: '77777777-7777-4777-8777-777777777777',
        label: 'Motif cible',
        normalized_label: 'motif cible',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 1,
      target_created: false,
    }),
    isPending: false,
  })
  splitExistingMutationMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: {
        pattern_id: '77777777-7777-4777-8777-777777777777',
        label: 'Motif cible',
        normalized_label: 'motif cible',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 1,
      target_created: false,
    }),
    isPending: false,
  })
  splitNewMutationMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: {
        pattern_id: '88888888-8888-4888-8888-888888888888',
        label: 'Nouveau split',
        normalized_label: 'nouveau split',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 1,
      target_created: true,
    }),
    isPending: false,
  })
}

describe('AnalyticsPatternDetailPage', () => {
  afterEach(() => {
    cleanup()
    detailQueryMock.mockReset()
    patternSignalsQueryMock.mockReset()
    reportIssueMutationMock.mockReset()
    governanceTargetsQueryMock.mockReset()
    renameMutationMock.mockReset()
    mergeMutationMock.mockReset()
    moveMutationMock.mockReset()
    splitExistingMutationMock.mockReset()
    splitNewMutationMock.mockReset()
    notifySuccessMock.mockClear()
    queryClientMock.invalidateQueries.mockClear()
    switchEstablishmentMock.mockReset()
    authState.current = {
      bootstrap: null,
      isBootstrapping: false,
      isReady: true,
    }
  })

  it('does not fetch for Staff-only users', () => {
    setDetailQuery()
    authState.current = {
      bootstrap: bootstrap('staff'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(
      screen.getByText('Analytics est disponible pour les propriétaires, directeurs et managers.'),
    ).toBeTruthy()
    expect(detailQueryMock).toHaveBeenCalledWith(
      'pattern-1',
      analyticsState,
      expect.objectContaining({ enabled: false }),
    )
    expect(patternSignalsQueryMock).toHaveBeenCalledWith(
      'pattern-1',
      analyticsState,
      expect.objectContaining({ enabled: false }),
    )
  })

  it('renders backend detail fields without using a second URL state hook', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(detailQueryMock).toHaveBeenCalledWith(
      'pattern-1',
      analyticsState,
      expect.objectContaining({ enabled: true }),
    )
    expect(screen.getByRole('heading', { name: 'Retard livraison' })).toBeTruthy()
    expect(screen.getByText('Récurrent')).toBeTruthy()
    expect(screen.getByText('Tendance journalière')).toBeTruthy()
    expect(screen.getByText('Distribution par statut')).toBeTruthy()
    expect(screen.getByText('Établissements concernés')).toBeTruthy()
    expect(screen.getByText('BU responsables')).toBeTruthy()
    expect(screen.getByText('Signals du motif')).toBeTruthy()
    expect(screen.getByText('Signal retard')).toBeTruthy()
    expect(patternSignalsQueryMock).toHaveBeenCalledWith(
      'pattern-1',
      analyticsState,
      expect.objectContaining({ enabled: true, pageSize: 25 }),
    )
    expect(screen.queryByText(/raw/i)).toBeNull()
    expect(screen.queryByText(/prompt/i)).toBeNull()
  })

  it('hides the issue report action for Owner-only users', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(
      screen.queryByRole('button', { name: 'Signaler un regroupement incorrect' }),
    ).toBeNull()
  })

  it('shows Owner governance for active Owner memberships only', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.getByText('Gouvernance Owner')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Renommer' })).toBeTruthy()

    cleanup()
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.queryByText('Gouvernance Owner')).toBeNull()
  })

  it('does not use organization_id from the URL as a reliable Owner gating source', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner', {
        organizationId: '99999999-9999-4999-8999-999999999999',
      }),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.getByText('Gouvernance Owner')).toBeTruthy()
  })

  it('loads governance targets with an infinite query when choosing a target', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Fusionner' }))

    expect(governanceTargetsQueryMock).toHaveBeenLastCalledWith(
      'pattern-1',
      expect.objectContaining({
        enabled: true,
        pageSize: 20,
        q: '',
      }),
    )
    expect(screen.getByRole('button', { name: /Motif cible/ })).toBeTruthy()
  })

  it('submits a pattern issue report for a Director in the current organization', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ report_id: 'report-1' })
    setDetailQuery({ data: detail() })
    setReportIssueMutation({ mutateAsync })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    fireEvent.click(
      screen.getByRole('button', { name: 'Signaler un regroupement incorrect' }),
    )
    fireEvent.change(screen.getByLabelText('Commentaire optionnel'), {
      target: { value: 'Mauvais motif' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        patternId: '44444444-4444-4444-8444-444444444444',
        signalId: '55555555-5555-4555-8555-555555555555',
        body: {
          reason: 'wrong_pattern',
          comment: 'Mauvais motif',
        },
      })
    })
    expect(screen.getByText('Signalement envoyé pour revue.')).toBeTruthy()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('hides the issue report action when Director membership belongs to another known organization', () => {
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('director', {
        organizationId: '99999999-9999-4999-8999-999999999999',
      }),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(
      screen.queryByRole('button', { name: 'Signaler un regroupement incorrect' }),
    ).toBeNull()
  })

  it('uses an approximate Director/Manager hint only when no reliable organization context exists', () => {
    setDetailQuery({
      data: detail({
        drilldown_context: {
          ...detail().drilldown_context,
          organization_id: null,
        },
      }),
    })
    setPatternSignalsQuery({
      data: {
        pages: [
          signals({
            items: [
              {
                ...signals().items[0],
                establishment: {
                  id: 'unknown-establishment',
                  name: 'Spore inconnu',
                },
              },
            ],
          }),
        ],
      },
    })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }
    const stateWithoutOrganization = {
      ...analyticsState,
      organizationId: null,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={stateWithoutOrganization}
        onNavigate={vi.fn()}
      />,
    )

    expect(
      screen.getByRole('button', { name: 'Signaler un regroupement incorrect' }),
    ).toBeTruthy()
  })

  it('keeps the report sheet open on error and releases the submit lock', async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValueOnce(
        new AnalyticsApiError({
          status: 409,
          detail: 'Signal is no longer assigned to this pattern.',
          code: 'analytics_pattern_assignment_mismatch',
        }),
      )
      .mockResolvedValueOnce({ report_id: 'report-2' })
    setDetailQuery({ data: detail() })
    setReportIssueMutation({ mutateAsync })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    fireEvent.click(
      screen.getByRole('button', { name: 'Signaler un regroupement incorrect' }),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }))

    await waitFor(() => {
      expect(screen.getByText('Signal is no longer assigned to this pattern.')).toBeTruthy()
    })
    expect(screen.getByRole('dialog')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledTimes(2)
    })
    expect(screen.getByText('Signalement envoyé pour revue.')).toBeTruthy()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('blocks two rapid submits before TanStack pending state rerenders', () => {
    const mutateAsync = vi.fn(() => new Promise(() => undefined))
    setDetailQuery({ data: detail() })
    setReportIssueMutation({ mutateAsync, isPending: false })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    fireEvent.click(
      screen.getByRole('button', { name: 'Signaler un regroupement incorrect' }),
    )

    const submitButton = screen.getByRole('button', { name: 'Envoyer' })
    fireEvent.click(submitButton)
    fireEvent.click(submitButton)

    expect(mutateAsync).toHaveBeenCalledTimes(1)
  })

  it('submits rename through Owner governance and keeps the user on the source detail', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Nouveau motif',
        normalized_label: 'nouveau motif',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: null,
      moved_signal_count: 0,
      target_created: false,
    })
    setDetailQuery({ data: detail() })
    setOwnerGovernanceMutations()
    renameMutationMock.mockReturnValue({ mutateAsync, isPending: false })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }
    const navigate = vi.fn()

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Renommer' }))
    fireEvent.change(screen.getByLabelText('Nouveau libellé'), {
      target: { value: 'Nouveau motif' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        patternId: '44444444-4444-4444-8444-444444444444',
        body: { label: 'Nouveau motif' },
      })
    })
    expect(navigate).not.toHaveBeenCalled()
    expect(screen.getByText('Motif renommé en “Nouveau motif”.')).toBeTruthy()
  })

  it('navigates to the merge target before invalidating the source as inactive', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'merged',
        merged_into_pattern_id: '77777777-7777-4777-8777-777777777777',
      },
      target_pattern: {
        pattern_id: '77777777-7777-4777-8777-777777777777',
        label: 'Motif cible',
        normalized_label: 'motif cible',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 2,
      target_created: false,
    })
    setDetailQuery({ data: detail() })
    setOwnerGovernanceMutations()
    mergeMutationMock.mockReturnValue({ mutateAsync, isPending: false })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }
    const navigate = vi.fn()

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Fusionner' }))
    fireEvent.click(screen.getByRole('button', { name: /Motif cible/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith(
        expect.stringContaining('/analytics/patterns/77777777-7777-4777-8777-777777777777?'),
        { replace: true },
      )
    })
    expect(notifySuccessMock).toHaveBeenCalledWith({
      message: 'Fusion appliquée : 2 Signal(s) déplacé(s).',
      kind: 'updated',
    })
    expect(queryClientMock.invalidateQueries).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: expect.arrayContaining(['analytics', 'pattern-detail']),
        type: 'inactive',
      }),
    )
  })

  it('submits move with selected loaded Signals and blocks rapid double-submit', async () => {
    const mutateAsync = vi.fn(() => new Promise(() => undefined))
    setDetailQuery({ data: detail() })
    setOwnerGovernanceMutations()
    moveMutationMock.mockReturnValue({ mutateAsync, isPending: false })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Déplacer' }))
    fireEvent.click(screen.getByRole('button', { name: /Motif cible/ }))
    fireEvent.click(screen.getByLabelText(/Signal retard/))
    const submit = screen.getByRole('button', { name: 'Confirmer' })
    fireEvent.click(submit)
    fireEvent.click(submit)

    expect(mutateAsync).toHaveBeenCalledTimes(1)
    expect(mutateAsync).toHaveBeenCalledWith({
      patternId: '44444444-4444-4444-8444-444444444444',
      body: {
        target_pattern_id: '77777777-7777-4777-8777-777777777777',
        signal_ids: ['55555555-5555-4555-8555-555555555555'],
      },
    })
  })

  it('submits split to existing with selected loaded Signals and target pattern', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: {
        pattern_id: '77777777-7777-4777-8777-777777777777',
        label: 'Motif cible',
        normalized_label: 'motif cible',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 1,
      target_created: false,
    })
    setDetailQuery({ data: detail() })
    setOwnerGovernanceMutations()
    splitExistingMutationMock.mockReturnValue({ mutateAsync, isPending: false })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Split existant' }))
    fireEvent.click(screen.getByRole('button', { name: /Motif cible/ }))
    fireEvent.click(screen.getByLabelText(/Signal retard/))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        patternId: '44444444-4444-4444-8444-444444444444',
        body: {
          target_pattern_id: '77777777-7777-4777-8777-777777777777',
          signal_ids: ['55555555-5555-4555-8555-555555555555'],
        },
      })
    })
  })

  it('submits split to new and navigates to the created target with analytics context', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      source_pattern: {
        pattern_id: '44444444-4444-4444-8444-444444444444',
        label: 'Retard livraison',
        normalized_label: 'retard livraison',
        status: 'active',
        merged_into_pattern_id: null,
      },
      target_pattern: {
        pattern_id: '88888888-8888-4888-8888-888888888888',
        label: 'Nouveau split',
        normalized_label: 'nouveau split',
        status: 'active',
        merged_into_pattern_id: null,
      },
      moved_signal_count: 1,
      target_created: true,
    })
    setDetailQuery({ data: detail() })
    setOwnerGovernanceMutations()
    splitNewMutationMock.mockReturnValue({ mutateAsync, isPending: false })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }
    const navigate = vi.fn()

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Split nouveau' }))
    fireEvent.change(screen.getByLabelText('Libellé du nouveau motif'), {
      target: { value: 'Nouveau split' },
    })
    fireEvent.click(screen.getByLabelText(/Signal retard/))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        patternId: '44444444-4444-4444-8444-444444444444',
        body: {
          label: 'Nouveau split',
          signal_ids: ['55555555-5555-4555-8555-555555555555'],
        },
      })
    })
    expect(navigate).toHaveBeenCalledWith(
      expect.stringContaining('/analytics/patterns/88888888-8888-4888-8888-888888888888?'),
    )
  })

  it('opens a same-establishment Signal without switching establishment', () => {
    const navigate = vi.fn()
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Signal retard/ }))

    expect(switchEstablishmentMock).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith(
      '/signals/55555555-5555-4555-8555-555555555555?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&organization_id=11111111-1111-4111-8111-111111111111&establishment_ids=22222222-2222-4222-8222-222222222222&q=retard&recurrence=recurrent&responsible_business_unit_ids=33333333-3333-4333-8333-333333333333&responsible_business_unit_unassigned=true&signal_statuses=open&analytics_pattern_id=44444444-4444-4444-8444-444444444444',
    )
  })

  it('switches establishment before opening a Signal from another establishment', async () => {
    const navigate = vi.fn()
    switchEstablishmentMock.mockResolvedValue({})
    setDetailQuery({ data: detail() })
    setPatternSignalsQuery({
      data: {
        pages: [
          signals({
            items: [
              {
                ...signals().items[0],
                establishment: {
                  id: 'est-2',
                  name: 'Spore 2',
                },
              },
            ],
          }),
        ],
      },
    })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Signal retard/ }))

    await waitFor(() => {
      expect(switchEstablishmentMock).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })
    expect(navigate).toHaveBeenCalledWith(
      expect.stringContaining('/signals/55555555-5555-4555-8555-555555555555?'),
    )
  })

  it('does not navigate when establishment switch fails', async () => {
    const navigate = vi.fn()
    switchEstablishmentMock.mockRejectedValue(new Error('Switch failed'))
    setDetailQuery({ data: detail() })
    setPatternSignalsQuery({
      data: {
        pages: [
          signals({
            items: [
              {
                ...signals().items[0],
                establishment: {
                  id: 'est-2',
                  name: 'Spore 2',
                },
              },
            ],
          }),
        ],
      },
    })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="44444444-4444-4444-8444-444444444444"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Signal retard/ }))

    await waitFor(() => {
      expect(screen.getByText('Switch failed')).toBeTruthy()
    })
    expect(navigate).not.toHaveBeenCalled()
  })

  it('uses the backend bucket civil date for trend labels', () => {
    setDetailQuery({
      data: detail({
        trend_timezone: 'Pacific/Honolulu',
        trend: [
          {
            bucket_date: '2026-07-31',
            bucket_start: '2026-08-01T00:30:00.000Z',
            bucket_end: '2026-08-01T23:30:00.000Z',
            signal_count: 3,
          },
        ],
      }),
    })
    authState.current = {
      bootstrap: bootstrap('owner'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.getByText('31 juil.')).toBeTruthy()
    expect(screen.queryByText('01 août')).toBeNull()
  })

  it('uses the provided analytics state for Back navigation', () => {
    const navigate = vi.fn()
    setDetailQuery({ data: detail() })
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={navigate}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Retour aux motifs' }))

    expect(navigate).toHaveBeenCalledWith(
      '/analytics?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&organization_id=11111111-1111-4111-8111-111111111111&establishment_ids=22222222-2222-4222-8222-222222222222&q=retard&recurrence=recurrent&responsible_business_unit_ids=33333333-3333-4333-8333-333333333333&responsible_business_unit_unassigned=true&signal_statuses=open',
    )
  })

  it('renders not found as a non-revealing state', () => {
    setDetailQuery({
      isError: true,
      error: new AnalyticsApiError({
        status: 404,
        detail: 'Introuvable.',
        code: 'analytics_pattern_not_found',
      }),
    })
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      <AnalyticsPatternDetailPage
        patternId="pattern-1"
        analyticsState={analyticsState}
        onNavigate={vi.fn()}
      />,
    )

    expect(screen.getByText('Motif introuvable')).toBeTruthy()
    expect(screen.getByText(/introuvable ou non accessible/)).toBeTruthy()
  })
})
