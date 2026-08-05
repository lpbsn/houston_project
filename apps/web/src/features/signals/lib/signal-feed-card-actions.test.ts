import { describe, expect, it } from 'vitest'

import type { PermissionHints, SignalFeedItem } from '../types'

import {
  canOpenSignalFeedCardActions,
  getSignalFeedCardActionOptions,
} from './signal-feed-card-actions'

function hints(overrides: Partial<PermissionHints> = {}): PermissionHints {
  return {
    can_pin: false,
    can_mark_interesting: false,
    can_archive: false,
    can_cancel: false,
    can_resolve: false,
    can_create_linked_action_plan: false,
    can_qualify_routing: false,
    ...overrides,
  }
}

function feedItem(
  overrides: Partial<Pick<SignalFeedItem, 'permission_hints' | 'is_pinned'>> = {},
): Pick<SignalFeedItem, 'permission_hints' | 'is_pinned'> {
  return {
    is_pinned: false,
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

  it('returns true when can_mark_interesting is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_mark_interesting: true }))).toBe(true)
  })

  it('returns true when can_archive is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_archive: true }))).toBe(true)
  })

  it('returns true when can_resolve is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_resolve: true }))).toBe(true)
  })

  it('returns true when can_cancel is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_cancel: true }))).toBe(true)
  })

  it('returns false when only can_qualify_routing is true', () => {
    expect(canOpenSignalFeedCardActions(hints({ can_qualify_routing: true }))).toBe(false)
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

  it('returns mark_interesting action when can_mark_interesting', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_mark_interesting: true }) }),
      ),
    ).toEqual([
      { id: 'mark_interesting', label: 'Marquer comme intéressant', tone: 'neutral' },
    ])
  })

  it('returns archive action when can_archive', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_archive: true }) }),
      ),
    ).toEqual([{ id: 'archive', label: 'Archiver', tone: 'neutral' }])
  })

  it('does not return qualify action when can_qualify_routing', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_qualify_routing: true }) }),
      ),
    ).toEqual([])
  })

  it('returns resolve action when can_resolve', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_resolve: true }) }),
      ),
    ).toEqual([{ id: 'resolve', label: 'Marquer comme résolue', tone: 'success' }])
  })

  it('returns cancel action when can_cancel', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({ permission_hints: hints({ can_cancel: true }) }),
      ),
    ).toEqual([{ id: 'cancel', label: 'Annuler cette observation', tone: 'danger' }])
  })

  it('returns all actions in order when all permissions are granted', () => {
    expect(
      getSignalFeedCardActionOptions(
        feedItem({
          is_pinned: true,
          permission_hints: hints({
            can_pin: true,
            can_mark_interesting: true,
            can_archive: true,
            can_resolve: true,
            can_cancel: true,
          }),
        }),
      ),
    ).toEqual([
      { id: 'pin', label: 'Désépingler', tone: 'neutral' },
      { id: 'mark_interesting', label: 'Marquer comme intéressant', tone: 'neutral' },
      { id: 'archive', label: 'Archiver', tone: 'neutral' },
      { id: 'resolve', label: 'Marquer comme résolue', tone: 'success' },
      { id: 'cancel', label: 'Annuler cette observation', tone: 'danger' },
    ])
  })
})
