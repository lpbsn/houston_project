// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import {
  DISCOVERY_CAPTIONS_PATH,
  DISCOVERY_POSTER_PATH,
  DISCOVERY_SUMMARY,
  DISCOVERY_TITLE,
  DISCOVERY_UNAVAILABLE_MESSAGE,
  DiscoveryPage,
  PUBLIC_DISCOVERY_VIDEO_URL,
} from './discovery-page'

afterEach(() => {
  cleanup()
})

describe('DiscoveryPage', () => {
  it('keeps the presentation readable when the remote video fails', () => {
    render(<DiscoveryPage />)

    expect(screen.getByRole('img', { name: 'Logo Spore' })).toBeTruthy()
    expect(screen.getByText('spore')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: DISCOVERY_TITLE })).toBeTruthy()
    expect(screen.getByText(DISCOVERY_SUMMARY)).toBeTruthy()
    expect(screen.queryByRole('form')).toBeNull()
    expect(screen.queryByText(/démo/i)).toBeNull()

    const video = document.querySelector('video')
    expect(video).toBeTruthy()
    expect(video?.hasAttribute('autoplay')).toBe(false)
    expect(video?.getAttribute('preload')).toBe('none')
    expect(video?.hasAttribute('controls')).toBe(true)
    expect(video?.hasAttribute('playsinline')).toBe(true)
    expect(video?.hasAttribute('crossorigin')).toBe(false)
    expect(video?.getAttribute('poster')).toBe(DISCOVERY_POSTER_PATH)

    const source = video?.querySelector('source')
    expect(source?.getAttribute('src')).toBe(PUBLIC_DISCOVERY_VIDEO_URL)
    expect(PUBLIC_DISCOVERY_VIDEO_URL).toBe('https://media.spore-os.com/spore-discovery-v1.mp4')

    const track = video?.querySelector('track')
    expect(track?.getAttribute('kind')).toBe('captions')
    expect(track?.getAttribute('srclang')).toBe('fr')
    expect(track?.getAttribute('label')).toBe('Français')
    expect(track?.hasAttribute('default')).toBe(true)
    expect(track?.getAttribute('src')).toBe(DISCOVERY_CAPTIONS_PATH)
    expect(DISCOVERY_CAPTIONS_PATH.startsWith('/')).toBe(true)
    expect(DISCOVERY_CAPTIONS_PATH.startsWith('http')).toBe(false)

    fireEvent.error(video as HTMLVideoElement)

    expect(screen.getByRole('status').textContent).toBe(DISCOVERY_UNAVAILABLE_MESSAGE)
    expect(screen.getByRole('heading', { level: 1, name: DISCOVERY_TITLE })).toBeTruthy()
    expect(screen.getByText(DISCOVERY_SUMMARY)).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Logo Spore' })).toBeTruthy()
  })
})
