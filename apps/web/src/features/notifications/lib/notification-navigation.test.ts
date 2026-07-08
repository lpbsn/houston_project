import { describe, expect, it } from 'vitest'

import { buildNotificationItem } from '../test-fixtures'
import { resolveNotificationPath } from './notification-navigation'

describe('notification navigation', () => {
  it('resolves action plan execution and signal routes', () => {
    expect(
      resolveNotificationPath(
        buildNotificationItem({
          subject_type: 'action_plan_execution',
          subject_id: 'exec-1',
        }),
      ),
    ).toBe('/action-plans/executions/exec-1')
    expect(
      resolveNotificationPath(
        buildNotificationItem({
          subject_type: 'signal',
          subject_id: 'signal-1',
        }),
      ),
    ).toBe('/signals/signal-1')
  })

  it('resolves comment mention routes when navigation is present', () => {
    expect(
      resolveNotificationPath(
        buildNotificationItem({
          event_key: 'comment.mention.created',
          subject_type: 'comment',
          subject_id: 'comment-1',
          navigation: {
            parent_subject_type: 'signal',
            parent_subject_id: 'signal-1',
          },
        }),
      ),
    ).toBe('/signals/signal-1?tab=comments&commentId=comment-1')

    expect(
      resolveNotificationPath(
        buildNotificationItem({
          event_key: 'comment.mention.created',
          subject_type: 'comment',
          subject_id: 'comment-2',
          navigation: {
            parent_subject_type: 'action_plan_execution',
            parent_subject_id: 'exec-1',
          },
        }),
      ),
    ).toBe('/action-plans/executions/exec-1?tab=comments&commentId=comment-2')
  })

  it('returns null for comment notifications without navigation', () => {
    expect(
      resolveNotificationPath(
        buildNotificationItem({
          event_key: 'comment.mention.created',
          subject_type: 'comment',
          subject_id: 'comment-1',
          navigation: null,
        }),
      ),
    ).toBeNull()
  })
})
