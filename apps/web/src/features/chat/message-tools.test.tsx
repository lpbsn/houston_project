// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MessageTools } from './components/message-tools'
import { messageTool } from './workspace-api'
import type { ChatMessage } from './types'
vi.mock('./workspace-api', () => ({ messageTool: vi.fn() }))
vi.mock('@/components/ui/terrain', () => ({
  TerrainDialog: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div role="dialog">{children}</div> : null,
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
})
describe('partage explicite vers une observation', () => {
  it('ne partage rien avant confirmation et conserve les corrections et l’auteur', async () => {
    vi.mocked(messageTool).mockResolvedValue({ success: true })
    mount()
    fireEvent.click(screen.getByText('Créer une observation'))
    expect(messageTool).not.toHaveBeenCalled()
    const input = screen.getByLabelText('Texte de l’observation') as HTMLTextAreaElement
    expect(input.value).toContain('Marine')
    expect(screen.getByText(/Ce texte sortira/)).toBeTruthy()
    fireEvent.change(input, { target: { value: 'Marine signale une livraison retardée.' } })
    fireEvent.click(screen.getByText('Confirmer le partage'))
    await waitFor(() =>
      expect(messageTool).toHaveBeenCalledWith('e1', 'm1', {
        operation: 'observe',
        active: true,
        text: 'Marine signale une livraison retardée.',
      }),
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
  it('conserve le brouillon en cas de refus serveur sans annoncer de succès', async () => {
    vi.mocked(messageTool).mockRejectedValue(new Error('Droits insuffisants'))
    mount()
    fireEvent.click(screen.getByText('Créer une observation'))
    fireEvent.click(screen.getByText('Confirmer le partage'))
    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toContain('Droits insuffisants'),
    )
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.queryByText('Observation envoyée')).toBeNull()
  })
  it('ne coupe pas un long message et bloque le partage tant qu’il dépasse la limite', () => {
    mount({ ...message, body: 'a'.repeat(1200) })
    fireEvent.click(screen.getByText('Créer une observation'))
    expect(
      (screen.getByLabelText('Texte de l’observation') as HTMLTextAreaElement).value.length,
    ).toBeGreaterThan(1200)
    expect((screen.getByText('Confirmer le partage') as HTMLButtonElement).disabled).toBe(true)
  })
})
