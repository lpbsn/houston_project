export type { SignalFeedFilters } from './lib/signal-feed-filters'

export type SignalViewMode = 'personal' | 'general'

export type PermissionHints = {
  can_pin: boolean
  can_set_urgency: boolean
  can_cancel: boolean
  can_resolve: boolean
}

export type SignalFeedItem = {
  id: string
  title: string
  structured_summary_short: string
  status: string
  urgency: string
  is_pinned: boolean
  module_key: string
  domain_key: string
  subject_key: string
  operational_unit_key: string | null
  location_text: string
  media_count: number
  last_activity_at: string
  created_at: string
  reporter_display_name: string | null
  permission_hints: PermissionHints
}

export type SignalFeedAppliedFilters = {
  view_mode: SignalViewMode
  statuses: string[]
  module_keys: string[]
  domain_keys: string[]
  subject_keys: string[]
}

export type SignalFeedResponse = {
  items: SignalFeedItem[]
  next_cursor: string | null
  has_more: boolean
  applied_filters: SignalFeedAppliedFilters
}

export type SourceContext = {
  submitted_at: string | null
  reporter_display_name: string
  media_count: number
}

export type SignalDetail = SignalFeedItem & {
  structured_summary: string
  source_context: SourceContext
}
