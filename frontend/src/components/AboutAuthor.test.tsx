import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { AboutAuthorButton, AboutAuthorLink } from './AboutAuthor'

afterEach(cleanup)

describe('About the author', () => {
  it('opens from the "i" button, shows accurate content and closes with Escape', async () => {
    const user = userEvent.setup()
    render(<AboutAuthorButton />)
    const button = screen.getByRole('button', { name: 'About the author' })
    expect(button).toHaveAttribute('aria-haspopup', 'dialog')

    await user.click(button)
    const dialog = await screen.findByRole('dialog', { name: 'About the author' })
    expect(dialog).toHaveTextContent('Aakar Gupta')
    expect(dialog).toHaveTextContent('Student Developer')
    expect(dialog).toHaveTextContent('Vellore Institute of Technology, Chennai')
    expect(dialog).toHaveTextContent('Amazon Cognito')
    // CloudFront is not deployed, so it may only appear as planned work.
    expect(dialog).toHaveTextContent(/CloudFront is planned and not yet enabled/)
    // No registration number or contact details in the public section.
    expect(dialog).not.toHaveTextContent('24BRS1321')
    expect(dialog.textContent).not.toMatch(/@|https?:\/\//)

    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    // Focus returns to the trigger for keyboard users.
    expect(button).toHaveFocus()
  })

  it('closes with the close button and opens from the footer credit link', async () => {
    const user = userEvent.setup()
    render(<AboutAuthorLink>Aakar Gupta</AboutAuthorLink>)
    await user.click(screen.getByRole('button', { name: 'Aakar Gupta' }))
    expect(await screen.findByRole('dialog', { name: 'About the author' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('is reachable by keyboard', async () => {
    const user = userEvent.setup()
    render(<AboutAuthorButton />)
    await user.tab()
    expect(screen.getByRole('button', { name: 'About the author' })).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('dialog', { name: 'About the author' })).toBeInTheDocument()
  })
})
