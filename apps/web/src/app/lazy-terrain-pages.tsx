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

export const LazyExecutionUpcomingPage = lazy(() =>
  import('@/features/execution/pages/execution-upcoming-page').then((module) => ({
    default: module.ExecutionUpcomingPage,
  })),
)

export const LazyChatPage = lazy(() =>
  import('@/features/chat/pages/chat-page').then((module) => ({
    default: module.ChatPage,
  })),
)

export const LazyAnalyticsPage = lazy(() =>
  import('@/features/analytics/pages/analytics-page').then((module) => ({
    default: module.AnalyticsPage,
  })),
)

export const LazyAnalyticsPatternDetailPage = lazy(() =>
  import('@/features/analytics/pages/analytics-pattern-detail-page').then((module) => ({
    default: module.AnalyticsPatternDetailPage,
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

export const LazyProfileSwitchEstablishmentPage = lazy(() =>
  import('@/features/auth/pages/profile-switch-establishment-page').then((module) => ({
    default: module.ProfileSwitchEstablishmentPage,
  })),
)

export const LazyTeamPage = lazy(() =>
  import('@/features/auth/pages/team-page').then((module) => ({
    default: module.TeamPage,
  })),
)

export const LazyNotificationsCenterPage = lazy(() =>
  import('@/features/notifications/pages/notifications-center-page').then((module) => ({
    default: module.NotificationsCenterPage,
  })),
)

export const LazyTeamMemberDetailPage = lazy(() =>
  import('@/features/auth/pages/team-member-detail-page').then((module) => ({
    default: module.TeamMemberDetailPage,
  })),
)

export const LazyActionPlanHubPage = lazy(() =>
  import('@/features/action-plans/pages/action-plan-hub-page').then((module) => ({
    default: module.ActionPlanHubPage,
  })),
)

export const LazyActionPlanCreatePage = lazy(() =>
  import('@/features/action-plans/pages/action-plan-create-page').then((module) => ({
    default: module.ActionPlanCreatePage,
  })),
)

export const LazyActionPlanTemplateDetailPage = lazy(() =>
  import('@/features/action-plans/pages/action-plan-template-detail-page').then((module) => ({
    default: module.ActionPlanTemplateDetailPage,
  })),
)

export const LazyActionPlanExecutionDetailPage = lazy(() =>
  import('@/features/action-plans/pages/action-plan-execution-detail-page').then((module) => ({
    default: module.ActionPlanExecutionDetailPage,
  })),
)

export const LazyActionPlanExecutionEditPage = lazy(() =>
  import('@/features/action-plans/pages/action-plan-execution-edit-page').then((module) => ({
    default: module.ActionPlanExecutionEditPage,
  })),
)

export const LazyChatRealtimeProvider = lazy(() =>
  import('@/features/chat/components/chat-realtime-provider').then((module) => ({
    default: module.ChatRealtimeProvider,
  })),
)
