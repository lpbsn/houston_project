import { describe, expect, it } from 'vitest'

import { resolveNotificationPath } from './notification-navigation'

describe('notification navigation', () => {
  it('resolves action plan execution and signal routes', () => {
    expect(resolveNotificationPath('action_plan_execution', 'exec-1')).toBe(
      '/action-plans/executions/exec-1',
    )
    expect(resolveNotificationPath('signal', 'signal-1')).toBe('/signals/signal-1')
  })

  it('returns null for comment notifications', () => {
    expect(resolveNotificationPath('comment', 'comment-1')).toBeNull()
  })
})
