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
  it('returns false when no actionable permission', () => {
    expect(canOpenSignalFeedCardActions(hints())).toBe(false)
  })

  it('returns true when can_pin is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_pin: true }))).toBe(true)
  })

  it('returns true when can_set_urgency is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_set_urgency: true }))).toBe(true)
  })

  it('returns true when can_resolve is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_resolve: true }))).toBe(true)
  })

  it('returns true when can_cancel is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_cancel: true }))).toBe(true)
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
    ).toEqual([{ id: 'pin', label: 'Épingler', tone: 'neutral' }])
  })

  it('returns unpin action when can_pin and pinned', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          is_pinned: true,
          permission_hints: hints({ can_pin: true }),
        }),
      ),
    ).toEqual([{ id: 'pin', label: 'Désépingler', tone: 'neutral' }])
  })

  it('returns urgency action when can_set_urgency and normal priority', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_set_urgency: true }) }),
      ),
    ).toEqual([{ id: 'urgency', label: 'Marquer urgent', tone: 'neutral' }])
  })

  it('returns normal priority action when can_set_urgency and high urgency', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          urgency: 'high',
          permission_hints: hints({ can_set_urgency: true }),
        }),
      ),
    ).toEqual([{ id: 'urgency', label: 'Priorité normale', tone: 'neutral' }])
  })

  it('returns resolve action when can_resolve', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_resolve: true }) }),
      ),
    ).toEqual([{ id: 'resolve', label: 'Marquer résolu', tone: 'success' }])
  })

  it('returns cancel action when can_cancel', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_cancel: true }) }),
      ),
    ).toEqual([{ id: 'cancel', label: 'Annuler ce signal', tone: 'danger' }])
  })

  it('returns all actions in order when all permissions are granted', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          is_pinned: true,
          urgency: 'high',
          permission_hints: hints({
            can_pin: true,
            can_set_urgency: true,
            can_resolve: true,
            can_cancel: true,
          }),
        }),
      ),
    ).toEqual([
      { id: 'pin', label: 'Désépingler', tone: 'neutral' },
      { id: 'urgency', label: 'Priorité normale', tone: 'neutral' },
      { id: 'resolve', label: 'Marquer résolu', tone: 'success' },
      { id: 'cancel', label: 'Annuler ce signal', tone: 'danger' },
    ])
  })
})
