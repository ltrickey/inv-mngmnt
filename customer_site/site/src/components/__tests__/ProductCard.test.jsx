import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ProductCard from '../ProductCard'

describe('ProductCard', () => {
  const mockProduct = {
    barcode: '0123456789012',
    barcode_type: 'GTIN',
    name: 'Test Product',
    description: 'Test description',
    price: 9.99,
    image_url: '/images/test.jpg',
    primary_category: 'Dairy',
    secondary_category: 'Milk',
    tertiary_category: null,
    ingredients: ['Milk', 'Sugar']
  }

  it('renders product name', () => {
    render(<ProductCard product={mockProduct} />)
    expect(screen.getByText('Test Product')).toBeInTheDocument()
  })

  it('renders product price', () => {
    render(<ProductCard product={mockProduct} />)
    expect(screen.getByText('$9.99')).toBeInTheDocument()
  })

  it('renders product description', () => {
    render(<ProductCard product={mockProduct} />)
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('renders product image with correct alt text', () => {
    render(<ProductCard product={mockProduct} />)
    const image = screen.getByAltText('Test Product')
    expect(image).toBeInTheDocument()
    expect(image).toHaveAttribute('src', '/images/test.jpg')
  })

  it('renders barcode information', () => {
    render(<ProductCard product={mockProduct} />)
    expect(screen.getByText(/0123456789012/)).toBeInTheDocument()
    expect(screen.getByText(/GTIN/)).toBeInTheDocument()
  })

  it('renders primary category', () => {
    render(<ProductCard product={mockProduct} />)
    expect(screen.getByText(/Dairy/)).toBeInTheDocument()
  })

  it('renders ingredients list', () => {
    render(<ProductCard product={mockProduct} />)
    // Query the ingredients list specifically to avoid conflicts with category values
    const ingredientsList = screen.getByText('Ingredients:').closest('.detail-row')
    expect(ingredientsList).toBeInTheDocument()
    
    // Verify ingredients are in the list
    const listItems = ingredientsList.querySelectorAll('li')
    expect(listItems).toHaveLength(2)
    expect(listItems[0]).toHaveTextContent('Milk')
    expect(listItems[1]).toHaveTextContent('Sugar')
  })
})
