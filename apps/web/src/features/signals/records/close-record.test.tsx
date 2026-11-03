// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { CloseRecordDialog } from './shared'
import { updateRecord, type FieldRecord } from './api'
vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), updateRecord: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
it('ne clôture qu’après choix et confirmation, conserve le motif après un refus serveur', async () => {
  const close = vi.fn()
  vi.mocked(updateRecord).mockRejectedValueOnce(new Error('Des actions restent ouvertes.'))
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><CloseRecordDialog site="s" record={{ id: 'r', updated_at: '2026-11-03T12:00:00Z' } as FieldRecord} onClose={close} /></QueryClientProvider>)
  expect(updateRecord).not.toHaveBeenCalled()
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'acknowledged' } })
  fireEvent.click(screen.getByRole('button', { name: 'Confirmer la clôture' }))
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Des actions restent ouvertes.'))
  expect(updateRecord).toHaveBeenCalledWith('s', 'r', { expected_updated_at: '2026-11-03T12:00:00Z', stage: 'closed', closure_reason: 'acknowledged' })
  expect(close).not.toHaveBeenCalled()
  expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('acknowledged')
})
