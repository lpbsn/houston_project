// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { ActionPlanPoleBadges } from './action-plan-pole-badges'

afterEach(cleanup)
const restaurant = {
  id: 'restaurant', specific_name: 'Restaurant', color_index: 0,
  instance_description: '', active: true,
  generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
}
const bar = { ...restaurant, id: 'bar', specific_name: 'Bar', color_index: 1 }

it('deduplicates by identity and preserves colors through reordering and renaming', () => {
  const { rerender } = render(<ActionPlanPoleBadges pilot_business_unit={restaurant}
    involved_poles={[{ business_unit: bar }, { business_unit: restaurant }, { business_unit: bar }]} />)
  expect(screen.getAllByText('Restaurant')).toHaveLength(1)
  expect(screen.getAllByText('Bar')).toHaveLength(1)
  const restaurantStyle = screen.getByText('Restaurant').getAttribute('style')
  const barStyle = screen.getByText('Bar').getAttribute('style')
  expect(restaurantStyle).not.toBe(barStyle)
  rerender(<ActionPlanPoleBadges pilot_business_unit={bar}
    involved_poles={[{ business_unit: { ...restaurant, specific_name: 'Food Court' } }]} />)
  expect(screen.getByText('Food Court').getAttribute('style')).toBe(restaurantStyle)
  expect(screen.getByText('Bar').getAttribute('style')).toBe(barStyle)
})
