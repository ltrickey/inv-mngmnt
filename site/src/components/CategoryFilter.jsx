import React from 'react'
import CategoryGroup from './CategoryGroup'

/**
 * Category filter section component
 */
function CategoryFilter({ categories, selectedCategories, onCategoryToggle }) {
  // Group categories by level for display
  const groupedCategories = {
    primary: categories.filter(cat => cat.level === 'primary'),
    secondary: categories.filter(cat => cat.level === 'secondary'),
    tertiary: categories.filter(cat => cat.level === 'tertiary')
  }

  return (
    <div className="filter-section">
      <h2>Filter by Category</h2>
      
      <CategoryGroup
        title="Primary Categories"
        categories={groupedCategories.primary}
        selectedCategories={selectedCategories}
        onCategoryToggle={onCategoryToggle}
      />

      <CategoryGroup
        title="Secondary Categories"
        categories={groupedCategories.secondary}
        selectedCategories={selectedCategories}
        onCategoryToggle={onCategoryToggle}
      />

      <CategoryGroup
        title="Tertiary Categories"
        categories={groupedCategories.tertiary}
        selectedCategories={selectedCategories}
        onCategoryToggle={onCategoryToggle}
      />
    </div>
  )
}

export default CategoryFilter
