import type { components } from '@/api/generated/types'

export type ExecutionViewMode = 'personal' | 'general'

export type ActionDetail = components['schemas']['ActionDetail']
export type ActionFeedItem = components['schemas']['ActionFeedItem']
export type ActionCreateRequest = components['schemas']['ActionCreateRequest']
export type ExecutionFeedResponse = components['schemas']['ExecutionFeedResponse']
export type ExecutionFeedItem = components['schemas']['ExecutionFeedItem']
export type ActionPermissionHints = components['schemas']['ActionPermissionHints']
export type ScopedUserSearchResult = components['schemas']['ScopedUserSearchResult']
