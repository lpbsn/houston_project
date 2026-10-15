// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LandingContact } from './landing-contact'
import { sendContact } from '../contact-api'
vi.mock('../contact-api', () => ({ sendContact: vi.fn() }))
vi.mock('./contact-verification', () => ({ ContactVerification: ({ onToken }: { onToken: (v: string) => void }) => <button type="button" onClick={() => onToken('token')}>Vérifier</button> }))
afterEach(() => { cleanup(); vi.resetAllMocks() })
function fill() {
  for (const [label, value] of [['Nom et prénom', 'Camille'], ['E-mail professionnel', 'camille@example.com'], ['Établissement ou groupe', 'Boutique'], ['Votre message', 'Bonjour Spore']]) fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByText('Vérifier'))
}
describe('LandingContact', () => {
  it('waits for verification and delivery before showing success', async () => {
    let resolve!: () => void
    vi.mocked(sendContact).mockReturnValue(new Promise<void>(r => { resolve = r }))
    render(<LandingContact />)
    expect((screen.getByRole('button', { name: /Envoyer ma demande/ }) as HTMLButtonElement).disabled).toBe(true)
    fill(); fireEvent.submit(screen.getByRole('form'))
    await waitFor(() => expect(sendContact).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('status')).toBeNull()
    resolve(); expect((await screen.findByRole('status')).textContent).toContain('envoyée')
  })
  it('preserves fields on failure and reuses the request id on retry', async () => {
    vi.mocked(sendContact).mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce(undefined)
    render(<LandingContact />); fill(); fireEvent.submit(screen.getByRole('form'))
    await screen.findByRole('alert')
    expect((screen.getByLabelText('Votre message') as HTMLTextAreaElement).value).toBe('Bonjour Spore')
    fireEvent.click(screen.getByText('Vérifier')); fireEvent.submit(screen.getByRole('form'))
    await screen.findByRole('status')
    expect(vi.mocked(sendContact).mock.calls[0][0].requestId).toBe(vi.mocked(sendContact).mock.calls[1][0].requestId)
  })
})
