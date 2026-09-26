// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ReportPhotoDraft } from './report-photos-section'
import { ReportPhotosSection } from './report-photos-section'

describe('ReportPhotosSection', () => {
  afterEach(() => {
    cleanup()
  })

  const photo: ReportPhotoDraft = {
    localId: 'local-1',
    file: new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' }),
    previewUrl: 'blob:preview-1',
  }

  it('renders optional header and preview thumbnail with descriptive alt', () => {
    render(
      <ReportPhotosSection
        photos={[photo]}
        onPhotoSelect={vi.fn()}
        onRemovePhoto={vi.fn()}
      />,
    )

    expect(screen.getByText(/Ajouter des photos/)).toBeTruthy()
    expect(screen.getByText('Optionnel · 1/3')).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Aperçu de photo.jpg' })).toBeTruthy()
  })

  it('uses a compact field layout without the dashed block header', () => {
    render(
      <ReportPhotosSection
        layout="field"
        photos={[photo]}
        onPhotoSelect={vi.fn()}
        onRemovePhoto={vi.fn()}
      />,
    )

    expect(screen.getByText('Photos')).toBeTruthy()
    expect(screen.queryByText(/Ajouter des photos/)).toBeNull()
    const remove = screen.getByRole('button', { name: 'Supprimer photo.jpg' })
    expect(remove.className).toContain('min-h-12')
    expect(remove.className).toContain('min-w-12')
  })
})
