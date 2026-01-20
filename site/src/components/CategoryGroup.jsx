import React from 'react'
import CategoryCheckbox from './CategoryCheckbox'

/**
 * Category group component for displaying categories by level
 */
function CategoryGroup({ title, categories, selectedCategories, onCategoryToggle }) {
  if (categories.length === 0) {
    return null
  }

  return (
    <div className="category-group">
      <h3 className="category-group-title">{title}</h3>
      <div className="category-filters">
        {categories.map(category => (
          <CategoryCheckbox
            key={category.name}
            category={category}
            isChecked={selectedCategories.includes(category.name)}
            onToggle={onCategoryToggle}
          />
        ))}
      </div>
    </div>
  )
}

export default CategoryGroup
