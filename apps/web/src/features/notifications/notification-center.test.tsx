// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const onNavigate = vi.fn()

let unreadCount: number | undefined = 2

vi.mock('./hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./hooks')>()
  return {
    ...actual,
    useNotificationsUnreadCount: () => unreadCount,
  }
})

import { NotificationCenter } from './components/notification-center'

describe('NotificationCenter', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    onNavigate.mockClear()
    unreadCount = 2
  })

  it('shows unread badge on the bell button', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    expect(screen.getByRole('button', { name: 'Notifications' })).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#1B4FD8\\].rounded-full')).toBeTruthy()
  })

  it('hides unread badge when there are no unread notifications', () => {
    unreadCount = 0

    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    expect(screen.getByRole('button', { name: 'Notifications' })).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#1B4FD8\\].rounded-full')).toBeNull()
  })

  it('navigates to the notifications center when the bell is clicked', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))

    expect(onNavigate).toHaveBeenCalledWith('/notifications-center')
  })

  it('does not render a notification dropdown panel', () => {
    render(<NotificationCenter establishmentId="est-1" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))

    expect(screen.queryByRole('dialog', { name: 'Notifications' })).toBeNull()
  })
})
