"""Time control categorization and formatting utilities."""
from typing import Tuple


def categorize_time_control(time_control: str) -> str:
    """Categorize a time control string into standard categories.

    Args:
        time_control: Time control string (e.g., "3+0", "10+5", "correspondence")

    Returns:
        Category name: "bullet", "blitz", "rapid", "classical", or "correspondence"
    """
    if not time_control or time_control == "correspondence":
        return "correspondence"

    # Parse time control (format: "minutes+increment")
    try:
        if '+' in time_control:
            parts = time_control.split('+')
            initial_minutes = int(parts[0])
            increment = int(parts[1])

            # Calculate estimated game time (initial + 40 moves * increment)
            total_time = initial_minutes + (40 * increment / 60)

            # Categorize based on total estimated time
            # Bullet: < 3 minutes
            # Blitz: 3-10 minutes
            # Rapid: 10-30 minutes
            # Classical: 30+ minutes
            if total_time < 3:
                return "bullet"
            elif total_time < 10:
                return "blitz"
            elif total_time < 30:
                return "rapid"
            else:
                return "classical"
        else:
            # Handle formats without increment
            minutes = int(time_control)
            if minutes < 3:
                return "bullet"
            elif minutes < 10:
                return "blitz"
            elif minutes < 30:
                return "rapid"
            else:
                return "classical"
    except (ValueError, IndexError):
        # If we can't parse it, default to correspondence
        return "correspondence"


def format_display_name(time_control: str, category: str) -> str:
    """Create user-friendly display name for a time control.

    Args:
        time_control: Raw time control string
        category: Category from categorize_time_control()

    Returns:
        Formatted display name like "Blitz (3+0)" or "Correspondence"
    """
    # Capitalize category name
    category_name = category.capitalize()

    if time_control == "correspondence" or category == "correspondence":
        return "Correspondence"

    return f"{category_name} ({time_control})"


def get_category_icon(category: str) -> str:
    """Get emoji icon for a time control category.

    Args:
        category: Category name

    Returns:
        Emoji string
    """
    icons = {
        "bullet": "⚡",
        "blitz": "🔥",
        "rapid": "⏱️",
        "classical": "♟️",
        "correspondence": "📧"
    }
    return icons.get(category, "♟️")
