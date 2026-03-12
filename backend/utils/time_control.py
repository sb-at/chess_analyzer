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

    # Parse time control (format: "minutes+increment_seconds")
    # Lichess converts to this format before storing; Chess.com is normalized
    # at import time. Both arrive here as minutes+seconds.
    try:
        if '+' in time_control:
            parts = time_control.split('+')
            initial_minutes = int(parts[0])
            increment_seconds = int(parts[1])

            # Estimated total minutes: initial + 40 moves * increment
            total_minutes = initial_minutes + (40 * increment_seconds / 60)

            # Bullet:  < 3 min
            # Blitz:   3–10 min
            # Rapid:  10–30 min
            # Classical: 30+ min
            if total_minutes < 3:
                return "bullet"
            elif total_minutes < 10:
                return "blitz"
            elif total_minutes < 30:
                return "rapid"
            else:
                return "classical"
        else:
            # No increment — value is in minutes
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
