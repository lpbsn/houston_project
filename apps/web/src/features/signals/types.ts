import type { components } from '@/api/generated/types'

export type { SignalFeedFilters } from './lib/signal-feed-filters'

export type SignalViewMode = 'personal' | 'general'

export type PermissionHints = components['schemas']['PermissionHints']
export type SignalFeedItem = components['schemas']['SignalFeedItem']
export type SignalFeedResponse = components['schemas']['SignalFeedResponse']
export type SourceContext = components['schemas']['SourceContext']
export type SignalDetail = components['schemas']['SignalDetail']
