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
