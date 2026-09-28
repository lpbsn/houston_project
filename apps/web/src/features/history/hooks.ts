import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  type InfiniteData,
} from '@tanstack/react-query'

import {
  fetchCrossExecutionHistory,
  fetchCrossSignalHistory,
  fetchExecutionHistory,
  fetchSignalHistory,
  type ExecutionHistoryResponse,
  type HistoryKind,
  type HistoryPeriod,
  type HistoryQuery,
  type HistoryViewMode,
  type SignalHistoryResponse,
} from './api'

export type HistoryListSource = 'establishment' | 'cross'

type HistoryPageData = SignalHistoryResponse | ExecutionHistoryResponse

type HistoryListOptions = {
  source: HistoryListSource
  establishmentId: string | null
  kind: HistoryKind
  viewMode: HistoryViewMode
  period: HistoryPeriod
  status: string
  from?: string
  to?: string
  enabled?: boolean
}

function pageAdvanced(nextCursor: string | null, requestedCursor: string | undefined, itemCount: number) {
  if (!nextCursor || itemCount === 0) {
    return false
  }
  return nextCursor !== requestedCursor
}

function historyQueryKey(options: HistoryListOptions) {
  return [
    'history',
    options.source,
    options.establishmentId ?? 'cross',
    options.kind,
    options.viewMode,
    options.period,
    options.status,
    options.from ?? '',
    options.to ?? '',
  ] as const
}

function fetchHistoryPage(
  options: HistoryListOptions,
  cursor: string | undefined,
): Promise<HistoryPageData> {
  const query: HistoryQuery = {
    viewMode: options.viewMode,
    period: options.period,
    status: options.status,
    from: options.from,
    to: options.to,
    cursor,
    pageSize: 25,
  }
  if (options.kind === 'signals') {
    return options.source === 'cross'
      ? fetchCrossSignalHistory(query)
      : fetchSignalHistory(options.establishmentId ?? '', query)
  }
  return options.source === 'cross'
    ? fetchCrossExecutionHistory(query)
    : fetchExecutionHistory(options.establishmentId ?? '', query)
}

export function useHistoryList(options: HistoryListOptions) {
  const queryClient = useQueryClient()
  const enabled =
    options.enabled !== false &&
    (options.source === 'cross' || Boolean(options.establishmentId)) &&
    (options.period !== 'custom' || Boolean(options.from && options.to))

  const queryKey = historyQueryKey(options)
  const list = useInfiniteQuery<
    HistoryPageData,
    Error,
    InfiniteData<HistoryPageData>,
    readonly unknown[],
    string | undefined
  >({
    queryKey,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => fetchHistoryPage(options, pageParam),
    getNextPageParam: (lastPage, _pages, pageParam) => {
      if (!lastPage.has_more) {
        return undefined
      }
      if (!pageAdvanced(lastPage.next_cursor, pageParam, lastPage.items.length)) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled,
  })
  const refresh = useMutation({
    mutationFn: () => fetchHistoryPage(options, undefined),
    onSuccess: (page) => {
      queryClient.setQueryData<InfiniteData<HistoryPageData>>(queryKey, {
        pages: [page],
        pageParams: [undefined],
      })
    },
  })
  return {
    ...list,
    refresh: refresh.mutateAsync,
    isRefreshing: refresh.isPending,
    refreshError: refresh.error,
  }
}
