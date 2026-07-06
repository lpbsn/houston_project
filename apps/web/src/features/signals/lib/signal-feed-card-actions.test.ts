import { describe, expect, it } from 'vitest'

import type { PermissionHints, SignalFeedItem } from '../types'

import {
  canOpenSignalFeedCardActions,
  getSignalFeedCardActionOptions,
} from './signal-feed-card-actions'

function hints(overrides: Partial<PermissionHints> = {}): PermissionHints {
  return {
    can_pin: false,
    can_set_urgency: false,
    can_cancel: false,
    can_resolve: false,
    can_create_linked_action_plan: false,
    ...overrides,
  }
}

function feedItem(
  overrides: Partial<Pick<SignalFeedItem, 'permission_hints' | 'is_pinned' | 'urgency'>> = {},
): Pick<SignalFeedItem, 'permission_hints' | 'is_pinned' | 'urgency'> {
  return {
    is_pinned: false,
    urgency: 'normal',
    permission_hints: hints(),
    ...overrides,
  }
}

describe('canOpenSignalFeedCardActions', () => {
  it('returns false when no pin or urgency permission', () => {
    expect(canOpenSignalFeedCardActions(hints())).toBe(false)
  })

  it('returns true when can_pin is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_pin: true }))).toBe(true)
  })

  it('returns true when can_set_urgency is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_set_urgency: true }))).toBe(true)
  })
})

describe('getSignalFeedCardActionOptions', () => {
  it('returns no options when no permissions', () => {
    expect(getSignalFeedCardActionOptions(feedItem())).toEqual([])
  })

  it('returns pin action when can_pin and not pinned', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_pin: true }) }),
      ),
    ).toEqual([{ id: 'pin', label: 'Épingler' }])
  })

  it('returns unpin action when can_pin and pinned', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          is_pinned: true,
          permission_hints: hints({ can_pin: true }),
        }),
      ),
    ).toEqual([{ id: 'pin', label: 'Désépingler' }])
  })

  it('returns urgency action when can_set_urgency and normal priority', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_set_urgency: true }) }),
      ),
    ).toEqual([{ id: 'urgency', label: 'Marquer urgent' }])
  })

  it('returns normal priority action when can_set_urgency and high urgency', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          urgency: 'high',
          permission_hints: hints({ can_set_urgency: true }),
        }),
      ),
    ).toEqual([{ id: 'urgency', label: 'Priorité normale' }])
  })

  it('returns both actions when both permissions are granted', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          is_pinned: true,
          urgency: 'high',
          permission_hints: hints({ can_pin: true, can_set_urgency: true }),
        }),
      ),
    ).toEqual([
      { id: 'pin', label: 'Désépingler' },
      { id: 'urgency', label: 'Priorité normale' },
    ])
  })
})
