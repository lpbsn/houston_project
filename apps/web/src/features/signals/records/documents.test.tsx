// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { RecordDocuments } from './documents'
import { ProjectContents } from './organization'
import { listRecordDocuments, listRecords, type FieldRecord } from './api'
vi.mock('./api', async (original) => ({
  ...(await original<typeof import('./api')>()),
  listRecordDocuments: vi.fn(),
  listRecords: vi.fn(),
}))
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
function mount(child: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      {child}
    </QueryClientProvider>,
  )
}
it('ouvre la discussion originale d’un document et permet de chercher dans l’index', async () => {
  vi.mocked(listRecordDocuments).mockResolvedValue({
    items: [
      {
        id: 'doc',
        kind: 'document',
        content_type: 'application/pdf',
        size_bytes: 123,
        original_filename: 'Implantation.pdf',
        preview_url: '/preview',
        thumbnail_url: null,
        comment_id: 'message',
        created_at: '2026-11-04T10:00:00Z',
        author_display_name: 'Charly',
        execution_id: 'execution',
        execution_title: 'Installer le podium',
      },
    ],
    next_offset: null,
  })
  const navigate = vi.fn(),
    work = vi.fn()
  mount(
    <RecordDocuments
      site="site"
      record={{ id: 'r' } as FieldRecord}
      onNavigate={navigate}
      onWork={work}
    />,
  )
  await screen.findByText('Implantation.pdf')
  fireEvent.click(
    screen.getByRole('button', {
      name: /Installer le podium · voir le message/,
    }),
  )
  expect(navigate).toHaveBeenCalledWith(
    '/e/site/execution/execution?tab=comments&commentId=message',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Partager dans un plan' }))
  expect(work).toHaveBeenCalledOnce()
  fireEvent.change(screen.getByLabelText('Rechercher un document'), {
    target: { value: 'implant' },
  })
  await waitFor(() =>
    expect(listRecordDocuments).toHaveBeenLastCalledWith(
      'site',
      'r',
      0,
      'implant',
    ),
  )
})
it('ne présente pas un échec des documents comme un dossier vide', async () => {
  vi.mocked(listRecordDocuments).mockRejectedValue(
    new Error('Accès indisponible.'),
  )
  mount(
    <RecordDocuments
      site="site"
      record={{ id: 'r' } as FieldRecord}
      onNavigate={vi.fn()}
      onWork={vi.fn()}
    />,
  )
  await screen.findByText('Accès indisponible.')
  expect(screen.queryByText(/Aucun document disponible/)).toBeNull()
})
it('montre uniquement le compteur accessible et garde la navigation vers les vraies fiches', async () => {
  vi.mocked(listRecords).mockResolvedValue({
    items: [
      {
        id: 'child',
        title: 'Réception du mobilier',
        pole: 'Jardin',
        stage: 'doing',
        owner: null,
        due_on: null,
      } as FieldRecord,
    ],
    next_offset: null,
    timezone: 'Europe/Paris',
  })
  const open = vi.fn()
  mount(
    <ProjectContents
      site="site"
      record={
        {
          id: 'project',
          visible_child_count: 1,
          visible_closed_child_count: 0,
          can_manage: false,
        } as FieldRecord
      }
      onOpen={open}
      onCreate={vi.fn()}
    />,
  )
  fireEvent.click(
    await screen.findByRole('button', { name: /Réception du mobilier/ }),
  )
  expect(open).toHaveBeenCalledWith('child')
  expect(screen.getByRole('progressbar').getAttribute('aria-valuemax')).toBe(
    '1',
  )
  expect(screen.queryByRole('button', { name: 'Ajouter une fiche' })).toBeNull()
})
