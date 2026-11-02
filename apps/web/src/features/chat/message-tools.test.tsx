// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MessageTools } from './components/message-tools'
import { messageTool } from './workspace-api'
import type { ChatMessage } from './types'

const { trackObservation, membership } = vi.hoisted(() => ({
  trackObservation: vi.fn(),
  membership: {
    current: { id: 'mem-1', establishment_id: 'e1' } as {
      id: string
      establishment_id: string
    } | null,
  },
}))

vi.mock('./workspace-api', () => ({ messageTool: vi.fn() }))
vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      memberships: membership.current
        ? [{ ...membership.current, status: 'active' as const }]
        : [],
      active_membership: membership.current,
    },
  }),
}))
vi.mock('@/features/observations/components/observation-processing-tracker-provider', () => ({
  trackObservation,
}))
vi.mock('@/components/ui/terrain', () => ({
  TerrainDialog: ({
    open,
    title,
    description,
    children,
  }: {
    open: boolean
    title?: string
    description?: React.ReactNode
    children: React.ReactNode
  }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        {description}
        {children}
      </div>
    ) : null,
}))
const message = {
  id: 'm1',
  body: 'La livraison est arrivée en retard.',
  author_display_name: 'Marine',
  created_at: '2026-10-30T09:00:00Z',
} as ChatMessage
function mount(value = message) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MessageTools establishmentId="e1" conversationId="c1" message={value} />
    </QueryClientProvider>,
  )
}
afterEach(cleanup)
beforeEach(() => {
  vi.mocked(messageTool).mockReset()
  trackObservation.mockReset()
  membership.current = { id: 'mem-1', establishment_id: 'e1' }
})
describe('partage explicite vers une observation', () => {
  it('ne partage rien avant confirmation, sépare la provenance et conserve les corrections', async () => {
    vi.mocked(messageTool).mockResolvedValue({ success: true })
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    expect(messageTool).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog', { name: 'Créer une observation' })).toBeTruthy()
    expect(screen.getByText('Marine')).toBeTruthy()
    expect(screen.getByText(/\d{2}\/\d{2}\/\d{4} · \d{2}:\d{2}:\d{2}/)).toBeTruthy()
    expect(screen.getByText(/pièces jointes ne sont pas transférées/)).toBeTruthy()
    expect(screen.getByText(/règles de visibilité de l’établissement/)).toBeTruthy()
    const input = screen.getByLabelText('Texte de l’observation') as HTMLTextAreaElement
    expect(input.value).toBe('La livraison est arrivée en retard.')
    fireEvent.change(input, { target: { value: 'Marine signale une livraison retardée.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Créer l’observation' }))
    await waitFor(() =>
      expect(messageTool).toHaveBeenCalledWith('e1', 'm1', {
        operation: 'observe',
        active: true,
        text: 'Marine signale une livraison retardée.',
      }),
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(trackObservation).not.toHaveBeenCalled()
  })
  it('démarre le même suivi que le rapport lorsque l’auteur reçoit l’identifiant', async () => {
    vi.mocked(messageTool).mockResolvedValue({ success: true, target_id: 'obs-1' })
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Créer l’observation' }))
    await waitFor(() => expect(trackObservation).toHaveBeenCalledTimes(1))
    const input = trackObservation.mock.calls[0]?.[0]
    expect(input).toMatchObject({
      observationId: 'obs-1',
      establishmentId: 'e1',
      authorMembershipId: 'mem-1',
      origin: 'direct_report',
    })
    expect(Number.isNaN(Date.parse(input.submittedAt))).toBe(false)
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
  it('ne suit pas une observation dont l’identifiant n’est pas renvoyé à ce participant', async () => {
    vi.mocked(messageTool).mockResolvedValue({ success: true, target_id: null })
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Créer l’observation' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(trackObservation).not.toHaveBeenCalled()
  })
  it('ne suit pas sans adhésion active sur l’établissement', async () => {
    membership.current = { id: 'mem-other', establishment_id: 'autre' }
    vi.mocked(messageTool).mockResolvedValue({ success: true, target_id: 'obs-1' })
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Créer l’observation' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(trackObservation).not.toHaveBeenCalled()
  })
  it('annule sans partager', () => {
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(messageTool).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).toBeNull()
  })
  it('conserve le brouillon en cas de refus serveur sans annoncer de succès', async () => {
    vi.mocked(messageTool).mockRejectedValue(new Error('Droits insuffisants'))
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Créer l’observation' }))
    await waitFor(() =>
      expect(messageTool).toHaveBeenCalledWith('e1', 'm1', {
        operation: 'observe',
        active: true,
        text: 'La livraison est arrivée en retard.',
      }),
    )
    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toContain('Droits insuffisants'),
    )
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(
      (screen.getByLabelText('Texte de l’observation') as HTMLTextAreaElement).value,
    ).toBe('La livraison est arrivée en retard.')
    expect(screen.queryByText('Observation envoyée')).toBeNull()
    expect(trackObservation).not.toHaveBeenCalled()
  })
  it('ne coupe pas un long message et bloque le partage tant qu’il dépasse la limite', () => {
    mount({ ...message, body: 'a'.repeat(1200) })
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    const input = screen.getByLabelText('Texte de l’observation') as HTMLTextAreaElement
    expect(input.value).toBe('a'.repeat(1200))
    expect(screen.getByRole('alert').textContent).toMatch(/n’est coupé automatiquement/)
    expect(
      (screen.getByRole('button', { name: 'Créer l’observation' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })
  it('bloque la création tant que le texte est trop court', () => {
    mount({ ...message, body: 'TEST' })
    fireEvent.click(screen.getByRole('button', { name: 'Créer une observation' }))
    expect((screen.getByLabelText('Texte de l’observation') as HTMLTextAreaElement).value).toBe(
      'TEST',
    )
    expect(
      (screen.getByRole('button', { name: 'Créer l’observation' }) as HTMLButtonElement).disabled,
    ).toBe(true)
    expect(messageTool).not.toHaveBeenCalled()
  })
})
