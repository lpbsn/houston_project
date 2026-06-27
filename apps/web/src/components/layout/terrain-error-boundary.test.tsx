// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  TERRAIN_UNEXPECTED_ERROR_MESSAGE,
  TerrainErrorBoundary,
} from './terrain-error-boundary'

function ThrowWhen({ shouldThrow, label }: { shouldThrow: boolean; label: string }) {
  if (shouldThrow) {
    throw new Error('boom')
  }
  return <div>{label}</div>
}

describe('TerrainErrorBoundary', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders healthy children without fallback', () => {
    render(
      <TerrainErrorBoundary resetKey="route-a" navigate={vi.fn()}>
        <div>Contenu sain</div>
      </TerrainErrorBoundary>,
    )

    expect(screen.getByText('Contenu sain')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('shows fallback when a child throws during render', () => {
    render(
      <TerrainErrorBoundary resetKey="route-a" navigate={vi.fn()}>
        <ThrowWhen shouldThrow={true} label="hidden" />
      </TerrainErrorBoundary>,
    )

    const alert = screen.getByRole('alert')
    expect(alert.textContent).toContain(TERRAIN_UNEXPECTED_ERROR_MESSAGE)
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeTruthy()
    expect(screen.getByRole('button', { name: "Retour à l'accueil" })).toBeTruthy()
  })

  it('retries by resetting the boundary when the child recovers', () => {
    let shouldThrow = true

    function RecoveringChild() {
      if (shouldThrow) {
        throw new Error('boom')
      }
      return <div>Contenu récupéré</div>
    }

    render(
      <TerrainErrorBoundary resetKey="route-a" navigate={vi.fn()}>
        <RecoveringChild />
      </TerrainErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toBeTruthy()

    shouldThrow = false
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))

    expect(screen.getByText('Contenu récupéré')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('navigates home with replace when returning to accueil', () => {
    const navigate = vi.fn()

    render(
      <TerrainErrorBoundary resetKey="route-a" navigate={navigate}>
        <ThrowWhen shouldThrow={true} label="hidden" />
      </TerrainErrorBoundary>,
    )

    fireEvent.click(screen.getByRole('button', { name: "Retour à l'accueil" }))

    expect(navigate).toHaveBeenCalledWith('/reporting', { replace: true })
  })

  it('clears fallback when resetKey changes and the new child is healthy', () => {
    const { rerender } = render(
      <TerrainErrorBoundary resetKey="route-a" navigate={vi.fn()}>
        <ThrowWhen shouldThrow={true} label="hidden" />
      </TerrainErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toBeTruthy()

    rerender(
      <TerrainErrorBoundary resetKey="route-b" navigate={vi.fn()}>
        <ThrowWhen shouldThrow={false} label="Nouveau contenu sain" />
      </TerrainErrorBoundary>,
    )

    expect(screen.getByText('Nouveau contenu sain')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })
})
