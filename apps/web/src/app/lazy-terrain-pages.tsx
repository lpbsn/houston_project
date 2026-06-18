import { lazy } from 'react'

export const LazyReportPage = lazy(() =>
  import('@/features/observations/pages/report-page').then((module) => ({
    default: module.ReportPage,
  })),
)

export const LazySignalFeedPage = lazy(() =>
  import('@/features/signals/pages/signal-feed-page').then((module) => ({
    default: module.SignalFeedPage,
  })),
)

export const LazySignalDetailPage = lazy(() =>
  import('@/features/signals/pages/signal-detail-page').then((module) => ({
    default: module.SignalDetailPage,
  })),
)

export const LazyExecutionFeedPage = lazy(() =>
  import('@/features/execution/pages/execution-feed-page').then((module) => ({
    default: module.ExecutionFeedPage,
  })),
)

export const LazyActionCreatePage = lazy(() =>
  import('@/features/actions/pages/action-create-page').then((module) => ({
    default: module.ActionCreatePage,
  })),
)

export const LazyActionDetailPage = lazy(() =>
  import('@/features/actions/pages/action-detail-page').then((module) => ({
    default: module.ActionDetailPage,
  })),
)

export const LazyChatPage = lazy(() =>
  import('@/features/chat/pages/chat-page').then((module) => ({
    default: module.ChatPage,
  })),
)

export const LazyChatConversationPage = lazy(() =>
  import('@/features/chat/pages/chat-conversation-page').then((module) => ({
    default: module.ChatConversationPage,
  })),
)

export const LazyProfilePage = lazy(() =>
  import('@/features/auth/pages/profile-page').then((module) => ({
    default: module.ProfilePage,
  })),
)

export const LazyTeamPage = lazy(() =>
  import('@/features/auth/pages/team-page').then((module) => ({
    default: module.TeamPage,
  })),
)

export const LazyChecklistHubPage = lazy(() =>
  import('@/features/checklists/pages/checklist-hub-page').then((module) => ({
    default: module.ChecklistHubPage,
  })),
)

export const LazyChecklistTemplateCreatePage = lazy(() =>
  import('@/features/checklists/pages/checklist-template-create-page').then((module) => ({
    default: module.ChecklistTemplateCreatePage,
  })),
)

export const LazyChecklistTemplateDetailPage = lazy(() =>
  import('@/features/checklists/pages/checklist-template-detail-page').then((module) => ({
    default: module.ChecklistTemplateDetailPage,
  })),
)

export const LazyChecklistExecutionDetailPage = lazy(() =>
  import('@/features/checklists/pages/checklist-execution-detail-page').then((module) => ({
    default: module.ChecklistExecutionDetailPage,
  })),
)

export const LazyChatRealtimeProvider = lazy(() =>
  import('@/features/chat/components/chat-realtime-provider').then((module) => ({
    default: module.ChatRealtimeProvider,
  })),
)
