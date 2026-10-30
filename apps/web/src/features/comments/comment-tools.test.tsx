// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { CommentTools } from './components/comment-tools'
import { commentTool } from '@/features/chat/workspace-api'
import { fetchActionPlanExecutionDetail } from '@/features/action-plans/api'
import type { ExecutionCommentListItem } from './types'
vi.mock('@/features/chat/workspace-api', () => ({ commentTool: vi.fn() }))
vi.mock('@/features/action-plans/api', () => ({ fetchActionPlanExecutionDetail: vi.fn() }))
vi.mock('@/components/ui/terrain', () => ({
  TerrainDialog: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div role="dialog">{children}</div> : null,
}))
const item = {
  id: 'comment1',
  body: 'Il manque les affiches.',
  can_create_task: true,
  permission_hints: { can_resolve: true },
  item_type: 'execution_thread',
} as ExecutionCommentListItem
beforeEach(() => {
  vi.mocked(commentTool).mockReset()
  vi.mocked(fetchActionPlanExecutionDetail).mockResolvedValue({
    assignees_by_pole: [],
  } as unknown as Awaited<ReturnType<typeof fetchActionPlanExecutionDetail>>)
})
afterEach(cleanup)
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <CommentTools establishmentId="e1" executionId="plan1" item={item} />
    </QueryClientProvider>,
  )
}
it('crée une tâche seulement après correction et confirmation', async () => {
  vi.mocked(commentTool).mockResolvedValue({ success: true, target_id: 'task1' })
  mount()
  fireEvent.click(screen.getByText('Créer une tâche'))
  expect(commentTool).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Action à réaliser'), {
    target: { value: 'Commander les affiches' },
  })
  await waitFor(() =>
    expect((screen.getByText('Confirmer la création') as HTMLButtonElement).disabled).toBe(false),
  )
  fireEvent.click(screen.getByText('Confirmer la création'))
  await waitFor(() =>
    expect(commentTool).toHaveBeenCalledWith('e1', 'comment1', {
      operation: 'task',
      active: true,
      title: 'Commander les affiches',
      assigned_membership_id: null,
      deadline_at: null,
    }),
  )
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
})
it('permet de corriger après un refus du plan sans annoncer une tâche créée', async () => {
  vi.mocked(commentTool).mockRejectedValue(new Error('Ce plan ne peut plus être modifié.'))
  mount()
  fireEvent.click(screen.getByText('Créer une tâche'))
  await waitFor(() =>
    expect((screen.getByText('Confirmer la création') as HTMLButtonElement).disabled).toBe(false),
  )
  fireEvent.click(screen.getByText('Confirmer la création'))
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('ne peut plus'))
  expect(screen.getByRole('dialog')).toBeTruthy()
  expect(screen.queryByText('Tâche créée dans ce plan')).toBeNull()
})
