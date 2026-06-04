import { describe, expect, it } from 'vitest'

import { MAX_VISIBLE_PHOTO_TILES, resolveVisiblePhotoTileCount } from './signal-detail-photo'

describe('resolveVisiblePhotoTileCount', () => {
  it('returns 0 for non-positive counts', () => {
    expect(resolveVisiblePhotoTileCount(0)).toBe(0)
    expect(resolveVisiblePhotoTileCount(-1)).toBe(0)
  })

  it('returns the count when within the cap', () => {
    expect(resolveVisiblePhotoTileCount(2)).toBe(2)
    expect(resolveVisiblePhotoTileCount(MAX_VISIBLE_PHOTO_TILES)).toBe(MAX_VISIBLE_PHOTO_TILES)
  })

  it('caps at MAX_VISIBLE_PHOTO_TILES', () => {
    expect(resolveVisiblePhotoTileCount(12)).toBe(MAX_VISIBLE_PHOTO_TILES)
  })
})
