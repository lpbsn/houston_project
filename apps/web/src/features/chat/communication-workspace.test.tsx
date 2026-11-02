// @vitest-environment jsdom
import type { ComponentProps } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { CommunicationWorkspace } from './components/communication-workspace'
import { fetchWorkspace } from './workspace-api'
import type { WorkspaceItem } from './workspace-api'

const navigate = vi.hoisted(() => vi.fn())
vi.mock('@/app/app-routes', () => ({ useAppRoute: () => ({ navigate }) }))
vi.mock('./hooks', () => ({
  useEligibleChatMembershipsQuery: () => ({
    data: {
      items: [{ membership_id: 'author-1', display_name: 'Marine' }],
    },
  }),
}))
vi.mock('./workspace-api', () => ({ fetchWorkspace: vi.fn() }))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function item(overrides: Partial<WorkspaceItem> = {}): WorkspaceItem {
  return {
    id: 'm1',
    kind: 'chat',
    parent_id: 'c1',
    title: 'Livraison',
    body: 'Le transporteur arrive',
    author: 'Marine',
    created_at: '2026-10-30T10:00:00Z',
    unread: false,
    unresolved: false,
    ...overrides,
  }
}

function renderWorkspace(
  props: Partial<ComponentProps<typeof CommunicationWorkspace>> = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onOpen = vi.fn()
  render(
    <QueryClientProvider client={client}>
      <CommunicationWorkspace
        establishmentId="e1"
        tab="search"
        mode="direct"
        onOpenItem={onOpen}
        {...props}
      />
    </QueryClientProvider>,
  )
  return { onOpen }
}

it('quitte les résultats pour ouvrir le message dans sa conversation', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({
    items: [item()],
    cursor: null,
  })
  const { onOpen } = renderWorkspace()
  fireEvent.click(await screen.findByText('Le transporteur arrive'))
  expect(onOpen).toHaveBeenCalledOnce()
  expect(navigate).toHaveBeenCalledWith('/e/e1/chat/c1?messageId=m1')
})

it('ouvre un aperçu desktop sans naviguer, puis le bouton vers le plan', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({
    items: [
      item({
        id: 'comment-1',
        kind: 'plan',
        parent_id: 'exec-1',
        title: 'Préparer la soirée',
        body: 'Valider le plan de salle',
        unresolved: true,
        unread: true,
      }),
    ],
    cursor: null,
  })
  const { onOpen } = renderWorkspace({ tab: 'plans', mode: 'pane' })
  fireEvent.click(await screen.findByRole('button', { name: /Préparer la soirée/ }))
  expect(navigate).not.toHaveBeenCalled()
  expect(onOpen).not.toHaveBeenCalled()
  expect(screen.getByTestId('workspace-preview').textContent).toContain('Valider le plan de salle')
  expect(screen.getAllByText('Commentaire non résolu').length).toBeGreaterThan(0)
  fireEvent.click(screen.getByRole('button', { name: 'Ouvrir dans le plan' }))
  expect(onOpen).toHaveBeenCalledOnce()
  expect(navigate).toHaveBeenCalledWith(
    '/e/e1/execution/exec-1?tab=comments&commentId=comment-1',
  )
})

it('navigue au clic en mode direct', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({
    items: [
      item({
        id: 'comment-1',
        kind: 'plan',
        parent_id: 'exec-1',
        title: 'Préparer la soirée',
      }),
    ],
    cursor: null,
  })
  const { onOpen } = renderWorkspace({ tab: 'plans', mode: 'direct' })
  fireEvent.click(await screen.findByRole('button', { name: /Préparer la soirée/ }))
  expect(onOpen).toHaveBeenCalledOnce()
  expect(navigate).toHaveBeenCalledWith(
    '/e/e1/execution/exec-1?tab=comments&commentId=comment-1',
  )
  expect(screen.queryByTestId('workspace-preview')).toBeNull()
})

it('affiche les libellés de commentaires et centre une liste de mentions vide', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({ items: [], cursor: null })
  renderWorkspace({ tab: 'plans', mode: 'pane' })
  expect(await screen.findByRole('heading', { name: 'Commentaires des plans d’action' })).toBeTruthy()
  expect(screen.getByText('Retrouvez les commentaires associés à vos plans d’action.')).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Plans avec commentaires' })).toBeTruthy()
  expect(screen.queryByText('Les tâches restent dans leurs plans')).toBeNull()

  cleanup()
  renderWorkspace({ tab: 'mentions', mode: 'pane' })
  const empty = await screen.findByText('Aucune mention pour le moment')
  expect(empty.className).toContain('italic')
  expect(empty.className).toContain('text-center')
})

it('envoie unresolved=true seulement pour le filtre Plans', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({ items: [], cursor: null })
  renderWorkspace({ tab: 'plans', mode: 'direct' })
  await waitFor(() => {
    expect(fetchWorkspace).toHaveBeenCalledWith(
      'e1',
      expect.objectContaining({ tab: 'plans', unresolved: false }),
    )
  })
  fireEvent.click(screen.getByRole('button', { name: 'Non résolues' }))
  await waitFor(() => {
    expect(fetchWorkspace).toHaveBeenCalledWith(
      'e1',
      expect.objectContaining({ tab: 'plans', unresolved: true }),
    )
  })

  cleanup()
  vi.mocked(fetchWorkspace).mockClear()
  renderWorkspace({ tab: 'mentions', mode: 'pane' })
  await waitFor(() => {
    expect(fetchWorkspace).toHaveBeenCalledWith(
      'e1',
      expect.objectContaining({ tab: 'mentions', unresolved: false }),
    )
  })
  expect(screen.queryByRole('button', { name: 'Non résolues' })).toBeNull()
})

it('n’affiche pas de pastille non lu sur les mentions', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({
    items: [
      item({
        unread: true,
        title: 'Restaurant & Bars',
        body: 'Peux-tu confirmer',
        author: 'Camille Martin',
      }),
    ],
    cursor: null,
  })
  renderWorkspace({ tab: 'mentions', mode: 'pane' })
  expect(await screen.findByText(/vous a mentionné dans/)).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Mentions' })).toBeTruthy()
  expect(screen.queryByText('Équipe et plans au même endroit')).toBeNull()
  expect(screen.getByText('Équipe')).toBeTruthy()
  expect(screen.queryByText('Non lu')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: /Restaurant & Bars/ }))
  expect(navigate).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Ouvrir la conversation' }))
  expect(navigate).toHaveBeenCalledWith('/e/e1/chat/c1?messageId=m1')
})

it('conserve auteur, date et pièces jointes dans la recherche', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({ items: [], cursor: null })
  renderWorkspace({ tab: 'search', mode: 'pane' })
  fireEvent.change(await screen.findByLabelText('Auteur'), { target: { value: 'author-1' } })
  fireEvent.change(screen.getByLabelText('Depuis'), { target: { value: '2026-03-01' } })
  fireEvent.click(screen.getByRole('checkbox', { name: 'Avec pièce jointe' }))
  fireEvent.change(screen.getByLabelText('Rechercher dans les messages'), {
    target: { value: 'livraison' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }))
  await waitFor(() => {
    expect(fetchWorkspace).toHaveBeenCalledWith(
      'e1',
      expect.objectContaining({
        tab: 'search',
        q: 'livraison',
        author_id: 'author-1',
        after: new Date('2026-03-01T00:00:00').toISOString(),
        files_only: true,
        unresolved: false,
      }),
    )
  })
})
