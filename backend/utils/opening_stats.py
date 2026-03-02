"""Opening statistics calculator."""
from typing import List, Dict
from collections import defaultdict


def calculate_opening_statistics(games: List[Dict]) -> Dict:
    """Calculate opening statistics from analyzed games.

    Args:
        games: List of game documents from MongoDB

    Returns:
        Dict with white_openings and black_openings statistics
    """
    white_openings = defaultdict(lambda: {
        'count': 0,
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'win_rate': 0.0,
        'eco': None
    })

    black_openings = defaultdict(lambda: {
        'count': 0,
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'win_rate': 0.0,
        'eco': None
    })

    for game in games:
        opening_name = game.get('opening_name') or game.get('opening_eco') or 'Unknown Opening'
        opening_eco = game.get('opening_eco')
        user_color = game.get('user_color', 'white')
        result = game.get('result', '')

        # Select the appropriate opening dictionary
        if user_color == 'white':
            opening_dict = white_openings
        else:
            opening_dict = black_openings

        # Update statistics
        stats = opening_dict[opening_name]
        stats['count'] += 1
        if opening_eco:
            stats['eco'] = opening_eco

        # Update win/loss/draw counts
        if (user_color == 'white' and result == '1-0') or \
           (user_color == 'black' and result == '0-1'):
            stats['wins'] += 1
        elif result == '1/2-1/2':
            stats['draws'] += 1
        else:
            stats['losses'] += 1

    # Calculate win rates and format results
    def format_openings(opening_dict):
        openings_list = []
        for opening, stats in opening_dict.items():
            total = stats['count']
            if total > 0:
                win_rate = (stats['wins'] / total) * 100
                stats['win_rate'] = round(win_rate, 1)

                openings_list.append({
                    'name': opening,
                    'eco': stats['eco'],
                    'count': stats['count'],
                    'wins': stats['wins'],
                    'draws': stats['draws'],
                    'losses': stats['losses'],
                    'win_rate': stats['win_rate']
                })

        # Sort by count (most played first)
        openings_list.sort(key=lambda x: x['count'], reverse=True)
        return openings_list

    return {
        'white_openings': format_openings(white_openings),
        'black_openings': format_openings(black_openings),
        'total_white_games': sum(stats['count'] for stats in white_openings.values()),
        'total_black_games': sum(stats['count'] for stats in black_openings.values())
    }
