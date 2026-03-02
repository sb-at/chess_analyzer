"""Opening pattern detection engine."""
from typing import List, Dict
from collections import defaultdict
import chess.pgn
from io import StringIO


class OpeningPatternDetector:
    """Detector for opening-related patterns."""

    def __init__(self):
        """Initialize opening pattern detector."""
        self.min_games_threshold = 3

    def detect(self, games: List[Dict]) -> List[Dict]:
        """Detect opening patterns across games.

        Args:
            games: List of analyzed games

        Returns:
            List of detected opening patterns
        """
        patterns = []

        # Analyze opening performance
        opening_stats = self._analyze_opening_stats(games)

        # Generate insights
        patterns.extend(self._detect_poor_openings(opening_stats))
        patterns.extend(self._detect_repeated_mistakes(opening_stats))

        return patterns

    def _analyze_opening_stats(self, games: List[Dict]) -> Dict:
        """Analyze statistics for each opening."""
        opening_stats = defaultdict(lambda: {
            'games': [],
            'total_games': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'total_accuracy': 0,
            'mistakes_by_move': defaultdict(list),
            'dates': []
        })

        for game in games:
            # Get opening info
            opening_name = game.get('opening_name') or game.get('opening_eco') or 'Unknown Opening'
            user_color = game.get('user_color', 'white')
            result = game.get('result', '')

            stats = opening_stats[opening_name]
            stats['games'].append(game.get('_id') or game.get('game_id'))
            stats['total_games'] += 1

            if game.get('date'):
                stats['dates'].append(game['date'])

            # Record result
            if (user_color == 'white' and result == '1-0') or \
               (user_color == 'black' and result == '0-1'):
                stats['wins'] += 1
            elif result == '1/2-1/2':
                stats['draws'] += 1
            else:
                stats['losses'] += 1

            # Analyze opening accuracy (first 20 plies = 10 moves)
            if game.get('analyzed') and game.get('moves'):
                opening_moves = [m for m in game['moves'] if m.get('move_number', 0) <= 10]

                if opening_moves:
                    avg_accuracy = sum(m.get('accuracy', 0) for m in opening_moves) / len(opening_moves)
                    stats['total_accuracy'] += avg_accuracy

                    # Track mistakes by move number
                    for move in opening_moves:
                        if move.get('is_mistake') or move.get('is_blunder'):
                            move_num = int(move.get('move_number', 0))
                            stats['mistakes_by_move'][move_num].append({
                                'game_id': game.get('_id') or game.get('game_id'),
                                'move': move.get('san'),
                                'best_move': move.get('best_move'),
                                'eval_loss': move.get('centipawn_loss', 0),
                                'fen': move.get('fen_before')
                            })

        # Calculate average accuracy
        for opening, data in opening_stats.items():
            if data['total_games'] > 0:
                data['avg_accuracy'] = data['total_accuracy'] / data['total_games']

        return opening_stats

    def _detect_poor_openings(self, stats: Dict) -> List[Dict]:
        """Detect openings with poor results."""
        patterns = []

        for opening, data in stats.items():
            if data['total_games'] < self.min_games_threshold:
                continue

            total_games = data['total_games']
            win_rate = (data['wins'] / total_games) * 100

            # Flag openings with poor win rate
            if win_rate < 40 and total_games >= 5:
                severity = (50 - win_rate) / 50  # 0-1 scale

                first_seen = min(data['dates']) if data['dates'] else None
                last_seen = max(data['dates']) if data['dates'] else None

                patterns.append({
                    'pattern_type': 'opening',
                    'pattern_subtype': 'poor_opening_results',
                    'opening_name': opening,
                    'description': f"Poor results in {opening} ({win_rate:.1f}% win rate)",
                    'frequency': total_games,
                    'win_rate': round(win_rate, 1),
                    'severity': severity,
                    'first_seen': first_seen,
                    'last_seen': last_seen,
                    'examples': data['games'][:5],
                    'metadata': {
                        'wins': data['wins'],
                        'draws': data['draws'],
                        'losses': data['losses'],
                        'avg_accuracy': round(data['avg_accuracy'], 1)
                    },
                    'recommendation': (
                        f"Consider reviewing or switching from {opening} "
                        f"(current win rate: {win_rate:.1f}% over {total_games} games)"
                    )
                })

        return patterns

    def _detect_repeated_mistakes(self, stats: Dict) -> List[Dict]:
        """Detect repeated mistakes in specific opening positions."""
        patterns = []

        for opening, data in stats.items():
            if data['total_games'] < self.min_games_threshold:
                continue

            # Check for moves with repeated mistakes
            for move_num, mistakes in data['mistakes_by_move'].items():
                if len(mistakes) >= 3:  # Repeated at least 3 times
                    avg_eval_loss = sum(m['eval_loss'] for m in mistakes) / len(mistakes)
                    severity = min(1.0, avg_eval_loss / 300)

                    first_seen = min(data['dates']) if data['dates'] else None
                    last_seen = max(data['dates']) if data['dates'] else None

                    # Create a descriptive title based on opening and move number
                    description = f"Repeated mistake on move {move_num} in {opening}"

                    patterns.append({
                        'pattern_type': 'opening',
                        'pattern_subtype': 'repeated_opening_mistake',
                        'opening_name': opening,
                        'description': description,
                        'move_number': move_num,
                        'frequency': len(mistakes),
                        'severity': severity,
                        'avg_eval_loss': round(avg_eval_loss, 1),
                        'first_seen': first_seen,
                        'last_seen': last_seen,
                        'examples': mistakes[:5],
                        'metadata': {
                            'opening_name': opening,
                            'move_number': move_num,
                            'avg_eval_loss': round(avg_eval_loss, 1)
                        },
                        'recommendation': (
                            f"You consistently make mistakes on move {move_num} in {opening}. "
                            "Review the correct move and understand the key ideas."
                        )
                    })

        return patterns
