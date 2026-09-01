// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { AccountDeletionPage } from './account-deletion-page'
import { ACCOUNT_DELETION_SUPPORT_EMAIL, accountDeletionContent } from '../content'

afterEach(() => {
  cleanup()
})

describe('AccountDeletionPage', () => {
  it('exposes in-app and email deletion paths for Spore', () => {
    render(<AccountDeletionPage />)

    expect(screen.getByTestId('account-deletion-page')).toBeTruthy()
    expect(
      screen.getByRole('heading', { level: 1, name: accountDeletionContent.pageTitle }),
    ).toBeTruthy()
    expect(screen.getByRole('link', { name: accountDeletionContent.loginLabel }).getAttribute('href')).toBe(
      accountDeletionContent.loginHref,
    )
    expect(screen.getByRole('link', { name: ACCOUNT_DELETION_SUPPORT_EMAIL }).getAttribute('href')).toContain(
      'mailto:',
    )
  })
})
