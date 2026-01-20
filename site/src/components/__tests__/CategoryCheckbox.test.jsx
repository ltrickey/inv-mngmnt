import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CategoryCheckbox from '../CategoryCheckbox'

describe('CategoryCheckbox', () => {
  const mockCategory = {
    name: 'Dairy',
    level: 'primary'
  }

  it('renders category name', () => {
    render(
      <CategoryCheckbox
        category={mockCategory}
        isChecked={false}
        onToggle={vi.fn()}
      />
    )
    expect(screen.getByText('Dairy')).toBeInTheDocument()
  })

  it('renders unchecked checkbox when isChecked is false', () => {
    render(
      <CategoryCheckbox
        category={mockCategory}
        isChecked={false}
        onToggle={vi.fn()}
      />
    )
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).not.toBeChecked()
  })

  it('renders checked checkbox when isChecked is true', () => {
    render(
      <CategoryCheckbox
        category={mockCategory}
        isChecked={true}
        onToggle={vi.fn()}
      />
    )
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeChecked()
  })

  it('calls onToggle when checkbox is clicked', async () => {
    const user = userEvent.setup()
    const mockToggle = vi.fn()
    
    render(
      <CategoryCheckbox
        category={mockCategory}
        isChecked={false}
        onToggle={mockToggle}
      />
    )
    
    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)
    
    expect(mockToggle).toHaveBeenCalledWith('Dairy')
  })
})
