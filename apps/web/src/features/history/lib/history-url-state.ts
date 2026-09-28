export type HistoryKind = 'signals' | 'executions'
export type HistoryViewMode = 'personal' | 'general'
export type HistoryPeriod = '7' | '30' | '90' | 'custom' | 'all'

export type HistoryUrlState = {
  kind: HistoryKind
  viewMode: HistoryViewMode
  period: HistoryPeriod
  status: string
  from: string
  to: string
  anchorId: string | null
}

const PERIODS = new Set<HistoryPeriod>(['7', '30', '90', 'custom', 'all'])

export function defaultHistoryViewMode(source: 'establishment' | 'cross'): HistoryViewMode {
  return source === 'cross' ? 'general' : 'personal'
}

export function defaultHistoryUrlState(source: 'establishment' | 'cross'): HistoryUrlState {
  return {
    kind: 'signals',
    viewMode: defaultHistoryViewMode(source),
    period: '30',
    status: 'all',
    from: '',
    to: '',
    anchorId: null,
  }
}

function statusForKind(kind: HistoryKind, status: string): string {
  if (status === 'all') {
    return 'all'
  }
  if (kind === 'signals' && (status === 'resolved' || status === 'canceled')) {
    return status
  }
  if (kind === 'executions' && (status === 'done' || status === 'canceled')) {
    return status
  }
  return 'all'
}

export function parseHistorySearch(
  search: string,
  source: 'establishment' | 'cross',
): HistoryUrlState {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const defaults = defaultHistoryUrlState(source)
  const kind = params.get('kind') === 'executions' ? 'executions' : 'signals'
  const viewMode = params.get('view_mode') === 'general' || params.get('view_mode') === 'personal'
    ? params.get('view_mode')
    : defaults.viewMode
  const periodValue = params.get('period')
  const period = PERIODS.has(periodValue as HistoryPeriod)
    ? (periodValue as HistoryPeriod)
    : defaults.period
  return {
    kind,
    viewMode: viewMode as HistoryViewMode,
    period,
    status: statusForKind(kind, params.get('status') ?? 'all'),
    from: params.get('from') ?? '',
    to: params.get('to') ?? '',
    anchorId: params.get('anchor'),
  }
}

export function serializeHistorySearch(
  state: HistoryUrlState,
  source: 'establishment' | 'cross',
): string {
  const defaults = defaultHistoryUrlState(source)
  const params = new URLSearchParams()
  if (state.kind !== defaults.kind) {
    params.set('kind', state.kind)
  }
  if (state.viewMode !== defaults.viewMode) {
    params.set('view_mode', state.viewMode)
  }
  if (state.period !== defaults.period) {
    params.set('period', state.period)
  }
  if (state.status !== 'all') {
    params.set('status', state.status)
  }
  if (state.period === 'custom') {
    if (state.from) {
      params.set('from', state.from)
    }
    if (state.to) {
      params.set('to', state.to)
    }
  }
  if (state.anchorId) {
    params.set('anchor', state.anchorId)
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export function historyReturnSearch(state: HistoryUrlState, source: 'establishment' | 'cross'): string {
  const current = serializeHistorySearch({ ...state, anchorId: state.anchorId }, source)
  const params = new URLSearchParams(current.startsWith('?') ? current.slice(1) : current)
  params.set('entry', 'history')
  const query = params.toString()
  return query ? `?${query}` : '?entry=history'
}

export function isHistoryReturnSearch(search: string): boolean {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  return params.get('entry') === 'history'
}

export function historySearchWithoutReturnFlag(search: string): string {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  params.delete('entry')
  const query = params.toString()
  return query ? `?${query}` : ''
}
