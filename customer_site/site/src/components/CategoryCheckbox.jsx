import React from 'react'

/**
 * Individual category checkbox component
 */
function CategoryCheckbox({ category, isChecked, onToggle }) {
  return (
    <label className="category-checkbox">
      <input
        type="checkbox"
        checked={isChecked}
        onChange={() => onToggle(category.name)}
      />
      {category.name}
    </label>
  )
}

export default CategoryCheckbox
