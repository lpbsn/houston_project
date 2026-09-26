// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TerrainHubSubheader } from './terrain-hub-subheader'

afterEach(() => {
  cleanup()
})

describe('TerrainHubSubheader', () => {
  it('renders without a default bottom border so hub feeds stay borderless', () => {
    const { container } = render(
      <TerrainHubSubheader>
        <span>Toolbar</span>
      </TerrainHubSubheader>,
    )

    const root = container.firstElementChild
    expect(root?.className).toContain('bg-white')
    expect(root?.className).not.toContain('border-b')
    expect(screen.getByText('Toolbar')).toBeTruthy()
  })

  it('still accepts an explicit bottom border via className', () => {
    const { container } = render(
      <TerrainHubSubheader className="border-b border-[#E8E6DF]">
        <span>Search</span>
      </TerrainHubSubheader>,
    )

    expect(container.firstElementChild?.className).toContain('border-b')
  })
})
