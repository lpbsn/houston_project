import { describe, expect, it } from 'vitest'

import * as lazyTerrainPages from '@/app/lazy-terrain-pages'

const LAZY_EXPORTS = [
  'LazyReportPage',
  'LazySignalFeedPage',
  'LazySignalDetailPage',
  'LazyExecutionFeedPage',
  'LazyActionCreatePage',
  'LazyActionDetailPage',
  'LazyChatPage',
  'LazyChatConversationPage',
  'LazyProfilePage',
  'LazyChecklistHubPage',
  'LazyChecklistTemplateCreatePage',
  'LazyChecklistTemplateDetailPage',
  'LazyChecklistQuickCreatePage',
  'LazyChecklistExecutionDetailPage',
  'LazyChatRealtimeProvider',
] as const

describe('lazy-terrain-pages', () => {
  it('exports a lazy component for each terrain route group', () => {
    for (const exportName of LAZY_EXPORTS) {
      const component = lazyTerrainPages[exportName]
      expect(component).toBeDefined()
      expect(typeof component).toBe('object')
    }
  })

  it('resolves terrain page modules on dynamic import', async () => {
    const modules = await Promise.all([
      import('@/features/observations/pages/report-page'),
      import('@/features/signals/pages/signal-feed-page'),
      import('@/features/execution/pages/execution-feed-page'),
      import('@/features/chat/pages/chat-page'),
      import('@/features/checklists/pages/checklist-hub-page'),
    ])

    expect(modules.every((module) => Object.keys(module).length > 0)).toBe(true)
  })
})
