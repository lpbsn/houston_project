// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { buildNotificationItem, buildNotificationListResponse } from './test-fixtures'
import { resolveNotificationPath } from './lib/notification-navigation'
import type { NotificationItem } from './types'

const fetchNextPage = vi.fn()
const refetch = vi.fn()
const markReadMutate = vi.fn()
const markAllReadMutate = vi.fn()
const onNavigate = vi.fn()

let queryFilter = 'all'
let queryState = {
  isLoading: false,
  isError: false,
  isSuccess: true,
  isFetchingNextPage: false,
  hasNextPage: false,
  data: {
    pages: [buildNotificationListResponse()],
    pageParams: [undefined],
  },
}

vi.mock('./hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./hooks')>()
  return {
    ...actual,
    useNotificationsInfiniteQuery: (_establishmentId: string, filter = 'all') => {
      queryFilter = filter
      return {
        ...queryState,
        refetch,
        fetchNextPage,
      }
    },
    useNotificationSelection: (
      _establishmentId: string | null,
      { onNavigate: navigate }: { onNavigate: (pathname: string) => void },
    ) => ({
      handleSelectNotification: (notification: NotificationItem) => {
        const path = resolveNotificationPath(notification)
        if (path) {
          navigate(path)
          if (notification.status === 'unread') {
            markReadMutate(notification.id)
          }
          return
        }
        if (notification.status === 'unread') {
          markReadMutate(notification.id)
        }
      },
    }),
    useMarkAllNotificationsReadMutation: () => ({
      mutate: markAllReadMutate,
      isPending: false,
    }),
  }
})

import { NotificationsCenterPage } from './pages/notifications-center-page'

const FIXED_NOW = new Date('2026-06-23T12:00:00')

describe('NotificationsCenterPage', () => {
  afterEach(() => {
    vi.useRealTimers()
    cleanup()
  })

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(FIXED_NOW)

    fetchNextPage.mockClear()
    refetch.mockClear()
    markReadMutate.mockClear()
    markAllReadMutate.mockClear()
    onNavigate.mockClear()
    queryFilter = 'all'

    queryState = {
      isLoading: false,
      isError: false,
      isSuccess: true,
      isFetchingNextPage: false,
      hasNextPage: false,
      data: {
        pages: [
          buildNotificationListResponse({
            items: [
              buildNotificationItem({
                id: 'notif-action-plan',
                subject_type: 'action_plan_execution',
                subject_id: 'exec-1',
                created_at: '2026-06-23T10:00:00.000Z',
              }),
            ],
            counts: { unread: 2 },
          }),
        ],
        pageParams: [undefined],
      },
    }
  })

  it('renders page title and unread count', () => {
    render(<NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />)

    expect(screen.getByRole('heading', { name: 'Centre de notifications' })).toBeTruthy()
    expect(screen.getByText('2 notifications non lues')).toBeTruthy()
  })

  it('applies brand active classes on the selected filter and unread count badge', () => {
    render(<NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />)

    const allTab = screen.getByRole('button', { name: 'Toutes' })
    const unreadTab = screen.getByRole('button', { name: /Non lues/ })

    expect(allTab.className).toContain('bg-[#114660]')
    expect(allTab.className).toContain('border-[#114660]')
    expect(unreadTab.className).not.toContain('bg-[#114660]')

    const unreadBadge = screen.getByText('2')
    expect(unreadBadge.className).toContain('bg-[#114660]')
  })

  it('renders unread notifications with chat-aligned unread dot color', () => {
    const { container } = render(
      <NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />,
    )

    expect(container.querySelector('.bg-\\[\\#4c8543\\].rounded-full')).toBeTruthy()
  })

  it('switches filter between all and unread', () => {
    render(<NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />)

    expect(queryFilter).toBe('all')

    fireEvent.click(screen.getByRole('button', { name: /Non lues/ }))
    expect(queryFilter).toBe('unread')

    fireEvent.click(screen.getByRole('button', { name: 'Toutes' }))
    expect(queryFilter).toBe('all')
  })

  it('shows unread-specific empty message when filter is unread', () => {
    queryState = {
      ...queryState,
      data: {
        pages: [buildNotificationListResponse({ items: [], counts: { unread: 0 } })],
        pageParams: [undefined],
      },
    }

    render(<NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: /Non lues/ }))
    expect(screen.getByText('0 notification non lue')).toBeTruthy()
    expect(screen.getByText('Vous êtes à jour.')).toBeTruthy()
    expect(screen.queryByText('Aucune notification non lue')).toBeNull()
  })

  it('navigates and marks notification read on click', () => {
    render(<NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByText('Nouveau plan d’action'))

    expect(onNavigate).toHaveBeenCalledWith('/action-plans/executions/exec-1')
    expect(markReadMutate).toHaveBeenCalledWith('notif-action-plan')
  })

  it('marks all notifications as read from the page header', () => {
    render(<NotificationsCenterPage establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Tout marquer comme lu' }))
    expect(markAllReadMutate).toHaveBeenCalled()
  })
})
