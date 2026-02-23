# Products Catalog - React Frontend

A React web application for browsing and filtering products from the products API.

## Features

- Select multiple categories to filter products
- View all product details including:
  - Name, description, and price
  - Barcode number and type (GTIN/PLU)
  - Primary, secondary, and tertiary categories
  - Ingredients list
  - Product images

## Setup

1. Install dependencies:
```bash
npm install
```

2. Make sure the Flask backend server is running on `http://localhost:8000`

3. Start the development server:
```bash
npm run dev
```

The React app will start on `http://localhost:3000`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm test` - Run tests in watch mode
- `npm run test:ui` - Run tests with UI interface
- `npm run test:coverage` - Run tests with coverage report

## Tech Stack

- React 18
- Vite (build tool)
- CSS for styling

## Component Structure

The application follows React best practices with a clear component hierarchy and separation of concerns. Components are organized in the `src/components/` directory.

### Component Hierarchy

```
App
├── CategoryFilter
│   └── CategoryGroup (×3)
│       └── CategoryCheckbox (×N)
├── Loading / Error
└── ProductsGrid
    └── ProductCard (×N)
        ├── ProductImage
        └── ProductInfo
            └── ProductDetails
```

### Component Descriptions

**Category Components:**
- `CategoryCheckbox` - Individual checkbox for a category
- `CategoryGroup` - Groups categories by level (primary/secondary/tertiary)
- `CategoryFilter` - Main filter section with all category groups

**Product Components:**
- `ProductImage` - Product image with error handling
- `ProductDetails` - Barcode, categories, and ingredients
- `ProductInfo` - Name, price, description, and details
- `ProductCard` - Complete product card (image + info)
- `ProductsGrid` - Grid container with empty state handling

**UI Components:**
- `Loading` - Loading indicator
- `Error` - Error message display

## Testing

The project uses **Vitest** and **React Testing Library** for component testing.

### Running Tests

```bash
# Run tests in watch mode (recommended for development)
npm test

# Run tests with UI interface
npm run test:ui

# Run tests with coverage report
npm run test:coverage
```

### Test Structure

Tests are located in `__tests__` directories next to their components:
- `src/components/__tests__/ProductCard.test.jsx`
- `src/components/__tests__/CategoryCheckbox.test.jsx`

### Testing Best Practices

- **Test user behavior**, not implementation details
- Use `screen.getByRole`, `screen.getByText`, etc. to query elements
- Use `@testing-library/user-event` for user interactions
- Keep tests focused and independent

### Example Test

```jsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProductCard from '../ProductCard'

it('renders product name', () => {
  render(<ProductCard product={mockProduct} />)
  expect(screen.getByText('Test Product')).toBeInTheDocument()
})
```
