// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppRouteProvider } from '@/app/app-routes'
import { createMemoryHistory } from '@/app/app-history'
import type { BootstrapResponse } from '@/features/auth/types'
import { rememberAccessArrival } from '@/features/install/arrival'

const fetchPlayStoreAccess = vi.hoisted(() => vi.fn(async () => 'none' as const))
const submitPlayStoreAccess = vi.hoisted(() => vi.fn(async () => undefined))
const qrToString = vi.hoisted(() => vi.fn(async (value: string) => `<svg>${value}</svg>`))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => true,
}))

vi.mock('@/features/install/api', () => ({
  fetchPlayStoreAccess,
  submitPlayStoreAccess,
}))

vi.mock('qrcode', () => ({
  default: { toString: qrToString },
}))

const bootstrapState = vi.hoisted(() => ({
  current: null as BootstrapResponse | null,
  authenticated: true,
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: bootstrapState.current,
    isAuthenticated: bootstrapState.authenticated,
  }),
}))

import { AndroidAccess } from '@/features/install/components/android-access'
import { AccessPage } from '@/features/install/pages/access-page'
import { InstallerPage } from '@/features/install/pages/installer-page'

const CLOSED_JOIN = 'https://play.google.com/apps/testing/app.spore'
const CLOSED_INSTALL = 'https://play.google.com/store/apps/details?id=app.spore'
const IOS_URL = 'https://apps.apple.com/fr/app/spore/id6810116036'

function operationalBootstrap(): BootstrapResponse {
  return {
    authenticated: true,
    user: { id: 'user-1', email: 'spore@example.com' },
    memberships: [
      {
        id: 'm-1',
        establishment_id: 'est-1',
        establishment_name: 'Hôtel des Mésanges',
        status: 'active',
      },
    ],
    active_membership: {
      id: 'm-1',
      establishment_id: 'est-1',
      establishment_name: 'Hôtel des Mésanges',
      status: 'active',
    },
    pending_onboarding_memberships: [],
  } as BootstrapResponse
}

function renderAt(path: string, node: ReactNode) {
  const history = createMemoryHistory(path)
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(AppRouteProvider, { history }, children)
  }
  render(node, { wrapper: Wrapper })
  return history
}

beforeEach(() => {
  bootstrapState.current = operationalBootstrap()
  bootstrapState.authenticated = true
})

afterEach(() => {
  cleanup()
  sessionStorage.clear()
  fetchPlayStoreAccess.mockReset()
  fetchPlayStoreAccess.mockResolvedValue('none')
  submitPlayStoreAccess.mockReset()
  submitPlayStoreAccess.mockResolvedValue(undefined)
  qrToString.mockClear()
  bootstrapState.current = operationalBootstrap()
  bootstrapState.authenticated = true
})

describe('AccessPage', () => {
  it('opens the App Store from the choice and explains the QR path', () => {
    const history = renderAt('/acces', createElement(AccessPage))
    const iphone = screen.getByRole('link', { name: 'Télécharger sur l’App Store' })
    expect(iphone.getAttribute('href')).toBe(IOS_URL)
    expect(iphone.getAttribute('target')).toBe('_blank')
    expect(screen.getByText(/choisissez Ordinateur et scannez le QR code/i)).toBeTruthy()
    expect(document.body.textContent).not.toContain(CLOSED_JOIN)
    expect(document.body.textContent).not.toContain(CLOSED_INSTALL)
    fireEvent.click(screen.getByRole('button', { name: 'Accéder directement au Web' }))
    expect(history.getHref()).toBe('/reporting')
  })

  it('shows the android request form without the SPORE email or Play links', async () => {
    renderAt('/acces?destination=android', createElement(AccessPage))
    const input = await screen.findByLabelText(/compte Google utilisé sur le Play Store/i)
    expect((input as HTMLInputElement).value).toBe('')
    expect((input as HTMLInputElement).value).not.toBe('spore@example.com')
    expect(screen.getByRole('button', { name: 'Demander mon accès' })).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Google Play/i })).toBeNull()
    expect(document.body.textContent).not.toContain(CLOSED_JOIN)
    expect(document.body.textContent).not.toContain(CLOSED_INSTALL)
  })

  it('shows a matching welcome once', async () => {
    rememberAccessArrival({
      userId: 'user-1',
      arrival: 'activated',
      establishmentId: 'est-1',
    })
    const first = renderAt('/acces', createElement(AccessPage))
    expect(screen.getByText('Votre compte SPORE est activé.')).toBeTruthy()
    await waitFor(() => {
      expect(sessionStorage.getItem('spore.access-arrival')).toBeNull()
    })
    void first
    cleanup()
    renderAt('/acces', createElement(AccessPage))
    expect(screen.queryByText('Votre compte SPORE est activé.')).toBeNull()
    expect(screen.getByText('Où souhaitez-vous utiliser SPORE ?')).toBeTruthy()
  })

  it('uses a generic question for another account', () => {
    rememberAccessArrival({
      userId: 'other-user',
      arrival: 'joined',
      establishmentId: 'est-1',
    })
    renderAt('/acces', createElement(AccessPage))
    expect(screen.queryByText(/Vous avez rejoint/)).toBeNull()
    expect(screen.getByText('Où souhaitez-vous utiliser SPORE ?')).toBeTruthy()
  })

  it('titles the computer page from the bootstrap', async () => {
    renderAt('/acces?destination=ordinateur', createElement(AccessPage))
    expect(screen.getByRole('heading', { name: 'Votre espace SPORE est prêt' })).toBeTruthy()
    await waitFor(() => {
      expect(qrToString).toHaveBeenCalledWith(expect.stringMatching(/\/installer$/), expect.anything())
    })
    const qrTarget = qrToString.mock.calls[0]?.[0] as string
    expect(qrTarget).not.toContain('token')
    expect(qrTarget).not.toContain('invitation')

    cleanup()
    bootstrapState.current = {
      ...operationalBootstrap(),
      memberships: [],
      active_membership: null,
      pending_onboarding_memberships: [
        {
          id: 'p-1',
          establishment_id: 'draft-1',
          establishment_name: 'Brouillon',
          establishment_status: 'draft',
          organization_id: 'org-1',
          organization_name: 'Org',
          role: 'staff',
          onboarding_session_id: null,
        },
      ],
    } as BootstrapResponse
    renderAt('/acces?destination=ordinateur', createElement(AccessPage))
    expect(screen.getByRole('heading', { name: 'Votre établissement est encore en préparation' })).toBeTruthy()
    expect(screen.queryByText('Votre espace SPORE est prêt')).toBeNull()
  })
})

describe('AndroidAccess distribution', () => {
  it('links to the store in public mode and hides the form', () => {
    render(
      createElement(AndroidAccess, {
        choice: { kind: 'store', href: 'https://play.google.com/store/apps/details?id=app.spore' },
        onContinueWeb: () => undefined,
        onChooseAnother: () => undefined,
      }),
    )
    const link = screen.getByRole('link', { name: 'Ouvrir Google Play' })
    expect(link.getAttribute('href')).toBe('https://play.google.com/store/apps/details?id=app.spore')
    expect(screen.queryByLabelText(/Play Store/i)).toBeNull()
  })

  it('shows an unavailable state without a form when the public URL is empty', () => {
    render(
      createElement(AndroidAccess, {
        choice: { kind: 'unavailable' },
        onContinueWeb: () => undefined,
        onChooseAnother: () => undefined,
      }),
    )
    expect(screen.getByText(/Lien Android indisponible/)).toBeTruthy()
    expect(screen.queryByLabelText(/Play Store/i)).toBeNull()
    expect(screen.queryByRole('link', { name: /Google Play/i })).toBeNull()
  })
})

describe('InstallerPage', () => {
  it('offers a manual choice and sends anonymous Android visitors to login', () => {
    bootstrapState.authenticated = false
    const history = renderAt('/installer', createElement(InstallerPage))
    const iphone = screen.getByRole('link', { name: 'Télécharger sur l’App Store' })
    expect(iphone.getAttribute('href')).toBe(IOS_URL)
    expect(iphone.getAttribute('target')).toBe('_blank')
    fireEvent.click(screen.getByRole('button', { name: 'Préparer l’accès à Google Play' }))
    expect(history.getHref()).toBe('/login?next=%2Facces%3Fdestination%3Dandroid')
    expect(document.body.textContent).not.toContain('token')
  })
})
