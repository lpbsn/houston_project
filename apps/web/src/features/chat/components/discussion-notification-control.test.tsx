// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { chatQueryKeys } from '../api'
import { DiscussionNotificationControl } from './discussion-notification-control'
import {
  setConversationNotifications,
  setPlanDiscussionPreference,
  type NotificationMode,
} from '../workspace-api'

vi.mock('../workspace-api', () => ({
  setConversationNotifications: vi.fn(),
  setPlanDiscussionPreference: vi.fn(),
}))

let chatMode: NotificationMode = 'all'
let planMode: NotificationMode = 'all'
const messagesFetch = vi.fn(async () => ({ items: [] }))
const workspaceFetch = vi.fn(async () => ({ items: [] }))

function ChatHarness() {
  const detail = useQuery({
    queryKey: chatQueryKeys.conversation('est-1', 'conv-1'),
    queryFn: async () => ({ notification_mode: chatMode }),
  })
  useQuery({
    queryKey: chatQueryKeys.messages('est-1', 'conv-1'),
    queryFn: messagesFetch,
  })
  useQuery({
    queryKey: ['chat', 'workspace', 'est-1'],
    queryFn: workspaceFetch,
  })
  return (
    <DiscussionNotificationControl
      establishmentId="est-1"
      parentId="conv-1"
      kind="chat"
      mode={detail.data?.notification_mode ?? 'all'}
      compact
    />
  )
}

function PlanHarness() {
  const preference = useQuery({
    queryKey: ['chat', 'plan-preference', 'est-1', 'exec-1'],
    queryFn: async () => ({ mode: planMode }),
  })
  useQuery({
    queryKey: chatQueryKeys.messages('est-1', 'conv-1'),
    queryFn: messagesFetch,
  })
  useQuery({
    queryKey: ['chat', 'workspace', 'est-1'],
    queryFn: workspaceFetch,
  })
  return (
    <DiscussionNotificationControl
      establishmentId="est-1"
      parentId="exec-1"
      kind="plan"
      mode={preference.data?.mode ?? 'all'}
    />
  )
}

function mount(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const invalidateSpy = vi.spyOn(client, 'invalidateQueries')
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
  return invalidateSpy
}

beforeEach(() => {
  chatMode = 'all'
  planMode = 'all'
  messagesFetch.mockClear()
  workspaceFetch.mockClear()
  vi.mocked(setConversationNotifications).mockReset()
  vi.mocked(setPlanDiscussionPreference).mockReset()
  vi.mocked(setConversationNotifications).mockImplementation(async (_establishmentId, _conversationId, mode) => {
    chatMode = mode
    return { success: true }
  })
  vi.mocked(setPlanDiscussionPreference).mockImplementation(async (_establishmentId, _executionId, body) => {
    planMode = body.mode ?? planMode
    return { success: true }
  })
})

afterEach(cleanup)

it('refreshes only the conversation preference when a chat notification mode changes', async () => {
  const invalidateSpy = mount(<ChatHarness />)
  const select = screen.getByLabelText('Notifications de cette discussion') as HTMLSelectElement
  await waitFor(() => expect(select.value).toBe('all'))
  await waitFor(() => expect(messagesFetch).toHaveBeenCalledTimes(1))
  await waitFor(() => expect(workspaceFetch).toHaveBeenCalledTimes(1))

  fireEvent.change(select, { target: { value: 'mentions' } })

  await waitFor(() => expect(select.value).toBe('mentions'))
  expect(setConversationNotifications).toHaveBeenCalledWith('est-1', 'conv-1', 'mentions')
  expect(invalidateSpy).toHaveBeenCalledWith({
    queryKey: chatQueryKeys.conversation('est-1', 'conv-1'),
  })
  expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['chat'] })
  expect(messagesFetch).toHaveBeenCalledTimes(1)
  expect(workspaceFetch).toHaveBeenCalledTimes(1)
})

it('refreshes only the plan preference when a plan notification mode changes', async () => {
  const invalidateSpy = mount(<PlanHarness />)
  const select = screen.getByLabelText('Notifications de cette discussion') as HTMLSelectElement
  await waitFor(() => expect(select.value).toBe('all'))
  await waitFor(() => expect(messagesFetch).toHaveBeenCalledTimes(1))
  await waitFor(() => expect(workspaceFetch).toHaveBeenCalledTimes(1))

  fireEvent.change(select, { target: { value: 'silent' } })

  await waitFor(() => expect(select.value).toBe('silent'))
  expect(setPlanDiscussionPreference).toHaveBeenCalledWith('est-1', 'exec-1', { mode: 'silent' })
  expect(invalidateSpy).toHaveBeenCalledWith({
    queryKey: ['chat', 'plan-preference', 'est-1', 'exec-1'],
  })
  expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['chat'] })
  expect(messagesFetch).toHaveBeenCalledTimes(1)
  expect(workspaceFetch).toHaveBeenCalledTimes(1)
})
