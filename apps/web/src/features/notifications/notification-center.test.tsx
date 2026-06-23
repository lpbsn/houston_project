// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { buildNotificationItem, buildNotificationListResponse } from './test-fixtures'

const fetchNextPage = vi.fn()
const refetch = vi.fn()
const markReadMutate = vi.fn()
const markAllReadMutate = vi.fn()
const onNavigate = vi.fn()

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

vi.mock('./hooks', () => ({
  useNotificationsInfiniteQuery: () => ({
    ...queryState,
    refetch,
    fetchNextPage,
  }),
  useMarkNotificationReadMutation: () => ({
    mutate: markReadMutate,
    isPending: false,
  }),
  useMarkAllNotificationsReadMutation: () => ({
    mutate: markAllReadMutate,
    isPending: false,
  }),
}))

import { NotificationCenter } from './components/notification-center'

describe('NotificationCenter', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    fetchNextPage.mockClear()
    refetch.mockClear()
    markReadMutate.mockClear()
    markAllReadMutate.mockClear()
    onNavigate.mockClear()

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
                id: 'notif-action',
                subject_type: 'action',
                subject_id: 'action-1',
                created_at: '2026-06-23T10:00:00.000Z',
              }),
              buildNotificationItem({
                id: 'notif-comment',
                event_key: 'comment.mention.created',
                subject_type: 'comment',
                subject_id: 'comment-1',
                title: 'Mention',
                body: 'Vous avez été mentionné dans un commentaire.',
                created_at: '2026-06-22T10:00:00.000Z',
              }),
            ],
            counts: { unread: 2 },
          }),
        ],
        pageParams: [undefined],
      },
    }
  })

  it('shows unread badge on the bell button', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    expect(screen.getByRole('button', { name: 'Notifications' })).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#1B4FD8\\].rounded-full')).toBeTruthy()
  })

  it('opens and closes the panel with toggle and escape', async () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeTruthy()

    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Notifications' })).toBeNull()
    })
  })

  it('closes the panel on outside pointerdown', async () => {
    render(
      <div>
        <button type="button">Outside</button>
        <NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />
      </div>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeTruthy()

    fireEvent.pointerDown(screen.getByRole('button', { name: 'Outside' }))
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Notifications' })).toBeNull()
    })
  })

  it('renders loading, empty, and error states', () => {
    queryState = {
      ...queryState,
      isLoading: true,
      isSuccess: false,
      data: undefined as never,
    }

    const { rerender } = render(
      <NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(document.querySelector('.animate-spin')).toBeTruthy()

    queryState = {
      isLoading: false,
      isError: false,
      isSuccess: true,
      isFetchingNextPage: false,
      hasNextPage: false,
      data: {
        pages: [buildNotificationListResponse({ items: [], counts: { unread: 0 } })],
        pageParams: [undefined],
      },
    }

    rerender(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)
    expect(screen.getByText('Aucune notification')).toBeTruthy()

    queryState = {
      isLoading: false,
      isError: true,
      isSuccess: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      data: undefined as never,
    }

    rerender(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)
    expect(screen.getByText('Impossible de charger les notifications.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(refetch).toHaveBeenCalled()
  })

  it('renders period sections and handles navigation and mark-read', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(screen.getByText('Aujourd’hui')).toBeTruthy()
    expect(screen.getAllByText('Hier').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByText('Nouvelle action'))
    expect(onNavigate).toHaveBeenCalledWith('/actions/action-1')
    expect(markReadMutate).toHaveBeenCalledWith('notif-action')
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).toBeNull()
  })

  it('marks comment notifications read without navigating', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    fireEvent.click(screen.getByText('Mention'))

    expect(onNavigate).not.toHaveBeenCalled()
    expect(markReadMutate).toHaveBeenCalledWith('notif-comment')
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeTruthy()
  })

  it('marks all notifications as read from the panel header', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    fireEvent.click(screen.getByRole('button', { name: 'Tout marquer comme lu' }))

    expect(markAllReadMutate).toHaveBeenCalled()
  })
})
