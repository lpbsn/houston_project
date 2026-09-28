import type { components } from '@/api/generated/types'

export type { SignalFeedFilters } from './lib/signal-feed-filters'

export type SignalViewMode = 'personal' | 'general'

export type PermissionHints = components['schemas']['PermissionHints']
export type SignalFeedItem = components['schemas']['SignalFeedItem']
export type SignalFeedCounts = components['schemas']['SignalFeedCounts']
export type SignalFeedResponse = components['schemas']['SignalFeedResponse']
export type SignalFeedPinsPage = components['schemas']['SignalFeedPinsResponse']
export type SignalPinReplacementCandidate = components['schemas']['SignalPinReplacementCandidate']
export type SourceContext = components['schemas']['SourceContext']
export type SignalDetail = components['schemas']['SignalDetail']
export type SignalQualifyRoutingRequest = components['schemas']['SignalQualifyRoutingRequest']
export type SignalQualifyRoutingResponse = components['schemas']['SignalQualifyRoutingResponse']
