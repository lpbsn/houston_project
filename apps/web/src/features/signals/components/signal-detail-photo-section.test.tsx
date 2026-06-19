// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SignalDetailPhotoSection } from './signal-detail-photo-section'

const mediaItems = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    preview_url: 'https://example.com/photo-1.jpg',
    content_type: 'image/jpeg',
    size_bytes: 1024,
    position: 1,
    observation_id: '22222222-2222-4222-8222-222222222222',
  },
]

afterEach(() => {
  document.body.style.overflow = ''
  cleanup()
})

describe('SignalDetailPhotoSection', () => {
  it('returns null when there are no media items', () => {
    const { container } = render(<SignalDetailPhotoSection mediaItems={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders real image previews from media items', () => {
    render(<SignalDetailPhotoSection mediaItems={mediaItems} />)
    const image = document.querySelector('img')
    expect(image?.getAttribute('src')).toBe(mediaItems[0].preview_url)
  })

  it('shows a camera fallback when image loading fails', async () => {
    render(<SignalDetailPhotoSection mediaItems={mediaItems} />)
    const image = document.querySelector('img')
    expect(image).not.toBeNull()
    fireEvent.error(image!)
    await waitFor(() => {
      expect(document.querySelector('img')).toBeNull()
    })
  })

  it('opens an enlarged preview modal when a photo tile is clicked', () => {
    render(<SignalDetailPhotoSection mediaItems={mediaItems} />)
    expect(screen.queryByRole('dialog')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Agrandir la photo' }))

    const dialog = screen.getByRole('dialog', { name: 'Aperçu photo' })
    const modalImage = dialog.querySelector('img')
    expect(modalImage?.getAttribute('src')).toBe(mediaItems[0].preview_url)
  })

  it('closes the enlarged preview modal when Fermer is clicked', () => {
    render(<SignalDetailPhotoSection mediaItems={mediaItems} />)
    fireEvent.click(screen.getByRole('button', { name: 'Agrandir la photo' }))
    screen.getByRole('dialog', { name: 'Aperçu photo' })

    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('locks body scroll while the preview modal is open', () => {
    render(<SignalDetailPhotoSection mediaItems={mediaItems} />)
    expect(document.body.style.overflow).toBe('')

    fireEvent.click(screen.getByRole('button', { name: 'Agrandir la photo' }))
    expect(document.body.style.overflow).toBe('hidden')

    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(document.body.style.overflow).toBe('')
  })

  it('closes the enlarged preview modal when the backdrop is clicked', () => {
    render(<SignalDetailPhotoSection mediaItems={mediaItems} />)
    fireEvent.click(screen.getByRole('button', { name: 'Agrandir la photo' }))
    screen.getByRole('dialog', { name: 'Aperçu photo' })

    fireEvent.click(screen.getByRole('button', { name: "Fermer l'aperçu" }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})

describe('SignalDetailPage photo section order', () => {
  it('keeps photo section before comments in the page module', async () => {
    const source = await vi.importActual<typeof import('../pages/signal-detail-page')>(
      '../pages/signal-detail-page',
    )
    const pageSource = source.SignalDetailPage.toString()
    expect(pageSource.indexOf('SignalDetailPhotoSection')).toBeGreaterThan(-1)
    expect(pageSource.indexOf('CommentSection')).toBeGreaterThan(-1)
    expect(pageSource.indexOf('SignalDetailPhotoSection')).toBeLessThan(
      pageSource.indexOf('CommentSection'),
    )
  })
})
