/**
 * Time control categorization and formatting utilities for frontend.
 */

export interface TimeControl {
  time_control: string
  display_name: string
  count: number
  category: string
}

/**
 * Get emoji icon for a time control category.
 */
export function getTimeControlIcon(category: string): string {
  const icons: { [key: string]: string } = {
    bullet: '⚡',
    blitz: '🔥',
    rapid: '⏱️',
    classical: '♟️',
    correspondence: '📧'
  }
  return icons[category] || '♟️'
}

/**
 * Get color class for a time control category.
 */
export function getCategoryColor(category: string): string {
  const colors: { [key: string]: string } = {
    bullet: 'yellow',
    blitz: 'red',
    rapid: 'blue',
    classical: 'purple',
    correspondence: 'gray'
  }
  return colors[category] || 'gray'
}

/**
 * Get Tailwind CSS classes for a category color.
 */
export function getCategoryColorClasses(category: string): {
  bg: string
  border: string
  hover: string
  text: string
} {
  const color = getCategoryColor(category)

  const colorClasses: { [key: string]: any } = {
    yellow: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-300',
      hover: 'hover:border-yellow-500 hover:shadow-md',
      text: 'text-yellow-700'
    },
    red: {
      bg: 'bg-red-50',
      border: 'border-red-300',
      hover: 'hover:border-red-500 hover:shadow-md',
      text: 'text-red-700'
    },
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-300',
      hover: 'hover:border-blue-500 hover:shadow-md',
      text: 'text-blue-700'
    },
    purple: {
      bg: 'bg-purple-50',
      border: 'border-purple-300',
      hover: 'hover:border-purple-500 hover:shadow-md',
      text: 'text-purple-700'
    },
    gray: {
      bg: 'bg-gray-50',
      border: 'border-gray-300',
      hover: 'hover:border-gray-500 hover:shadow-md',
      text: 'text-gray-700'
    }
  }

  return colorClasses[color] || colorClasses.gray
}

/**
 * Group time controls by category.
 */
export function groupByCategory(timeControls: TimeControl[]): { [category: string]: TimeControl[] } {
  const grouped: { [category: string]: TimeControl[] } = {}

  for (const tc of timeControls) {
    if (!grouped[tc.category]) {
      grouped[tc.category] = []
    }
    grouped[tc.category].push(tc)
  }

  return grouped
}

/**
 * Get ordered list of categories for display.
 */
export function getCategoryOrder(): string[] {
  return ['bullet', 'blitz', 'rapid', 'classical', 'correspondence']
}
