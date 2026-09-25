import type { AppRoute } from '@/app/app-routes'

type DesktopChatPageProps = {
  establishmentId: string | null
  selectedConversationId: string | null
}

/**
 * Single desktop-web chat surface for /chat, /e/:id/chat, and /chat/:id.
 * Cross /chat stays out (Coming Soon). Null when not desktop web or not this surface.
 *
 * `activeEstablishmentId` fills `/chat` and `/chat/:id` (session-scoped). Scoped
 * `/e/:id/chat` always uses the route establishment.
 */
export function resolveDesktopChatPageProps(
  route: AppRoute,
  isDesktopWeb: boolean,
  activeEstablishmentId: string | null = null,
): DesktopChatPageProps | null {
  if (!isDesktopWeb) {
    return null
  }

  if (route.kind === 'chat-conversation-detail') {
    return {
      establishmentId: activeEstablishmentId,
      selectedConversationId: route.conversationId,
    }
  }

  if (route.kind === 'static' && route.path === '/chat') {
    return {
      establishmentId: activeEstablishmentId,
      selectedConversationId: null,
    }
  }

  if (
    route.kind === 'scoped-terrain' &&
    route.page === 'chat' &&
    route.scope.type === 'establishment'
  ) {
    return {
      establishmentId: route.scope.establishmentId,
      selectedConversationId: null,
    }
  }

  return null
}

/** Shell / page remount key: stable across conversations, new on establishment change. */
export function desktopChatMountKey(establishmentId: string | null | undefined): string {
  return `chat:${establishmentId ?? 'none'}`
}

/** Shared height so Discussions and Conversation header bottom borders align. */
export const chatDesktopColumnHeaderClassName =
  'flex h-14 shrink-0 items-center border-b border-[#E8E6DF] bg-white px-3'
