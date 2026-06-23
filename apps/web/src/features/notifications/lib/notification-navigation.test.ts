import { describe, expect, it } from 'vitest'

import { resolveNotificationPath } from './notification-navigation'

describe('notification navigation', () => {
  it('resolves action, checklist execution, and signal routes', () => {
    expect(resolveNotificationPath('action', 'action-1')).toBe('/actions/action-1')
    expect(resolveNotificationPath('checklist_execution', 'exec-1')).toBe(
      '/checklists/executions/exec-1',
    )
    expect(resolveNotificationPath('signal', 'signal-1')).toBe('/signals/signal-1')
  })

  it('returns null for comment notifications', () => {
    expect(resolveNotificationPath('comment', 'comment-1')).toBeNull()
  })
})
