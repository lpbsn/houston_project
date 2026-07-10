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
    uploadId: 'upload-1',
    status: 'ready',
    previewUrl: 'blob:preview-1',
  }

  it('renders optional header and preview thumbnail with descriptive alt', () => {
    render(
      <ReportPhotosSection
        photos={[photo]}
        isUploadPending={false}
        onPhotoSelect={vi.fn()}
        onRemovePhoto={vi.fn()}
      />,
    )

    expect(screen.getByText(/Ajouter des photos/)).toBeTruthy()
    expect(screen.getByText('Optionnel · 1/3')).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Aperçu de photo.jpg' })).toBeTruthy()
  })
})
