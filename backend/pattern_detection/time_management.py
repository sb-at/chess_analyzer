"""Time management pattern detection engine."""
from typing import List, Dict
import statistics


class TimeManagementDetector:
    """Detector for time management patterns."""

    def __init__(self):
        """Initialize time management detector."""
        self.time_pressure_threshold = 60  # seconds

    def detect(self, games: List[Dict]) -> List[Dict]:
        """Detect time management patterns.

        Args:
            games: List of analyzed games

        Returns:
            List of detected time management patterns
        """
        patterns = []

        # Collect time-related data
        time_data = self._collect_time_data(games)

        # Detect patterns
        if time_data['has_time_data']:
            patterns.extend(self._detect_time_pressure_issues(time_data))
            patterns.extend(self._detect_time_trouble(time_data))

        return patterns

    def _collect_time_data(self, games: List[Dict]) -> Dict:
        """Collect time-related statistics from games."""
        accuracy_by_time = {
            'normal': [],
            'pressure': []
        }
        time_pressure_games = []
        has_time_data = False

        for game in games:
            if not game.get('analyzed'):
                continue

            moves = game.get('moves', [])
            game_had_time_pressure = False

            for move in moves:
                time_left = move.get('time_left')

                if time_left is not None:
                    has_time_data = True
                    accuracy = move.get('accuracy', 0)

                    # Categorize by time pressure
                    if time_left < self.time_pressure_threshold:
                        accuracy_by_time['pressure'].append(accuracy)
                        game_had_time_pressure = True
                    else:
                        accuracy_by_time['normal'].append(accuracy)

            # Check if game ended in severe time pressure
            if moves and moves[-1].get('time_left', float('inf')) < 30:
                time_pressure_games.append({
                    'game_id': game.get('_id') or game.get('game_id'),
                    'final_time': moves[-1].get('time_left'),
                    'result': game.get('result'),
                    'date': game.get('date')
                })

        return {
            'has_time_data': has_time_data,
            'accuracy_by_time': accuracy_by_time,
            'time_pressure_games': time_pressure_games
        }

    def _detect_time_pressure_issues(self, time_data: Dict) -> List[Dict]:
        """Detect accuracy drop under time pressure."""
        patterns = []

        accuracy_by_time = time_data['accuracy_by_time']

        if not accuracy_by_time['normal'] or not accuracy_by_time['pressure']:
            return patterns

        avg_normal = statistics.mean(accuracy_by_time['normal'])
        avg_pressure = statistics.mean(accuracy_by_time['pressure'])
        accuracy_drop = avg_normal - avg_pressure

        if accuracy_drop > 10:  # Significant drop
            severity = min(1.0, accuracy_drop / 30)

            patterns.append({
                'pattern_type': 'time_management',
                'pattern_subtype': 'time_pressure_accuracy_drop',
                'frequency': len(accuracy_by_time['pressure']),
                'severity': severity,
                'metadata': {
                    'avg_accuracy_normal': round(avg_normal, 1),
                    'avg_accuracy_pressure': round(avg_pressure, 1),
                    'accuracy_drop': round(accuracy_drop, 1)
                },
                'recommendation': (
                    f"Your accuracy drops {accuracy_drop:.1f}% under time pressure "
                    f"(avg: {avg_pressure:.1f}% vs {avg_normal:.1f}% normally). "
                    "Practice playing faster or use longer time controls."
                )
            })

        return patterns

    def _detect_time_trouble(self, time_data: Dict) -> List[Dict]:
        """Detect frequent time trouble."""
        patterns = []

        time_pressure_games = time_data['time_pressure_games']

        if len(time_pressure_games) >= 5:  # Frequent time trouble
            severity = min(1.0, len(time_pressure_games) / 20)

            # Get date range
            dates = [g['date'] for g in time_pressure_games if g.get('date')]
            first_seen = min(dates) if dates else None
            last_seen = max(dates) if dates else None

            patterns.append({
                'pattern_type': 'time_management',
                'pattern_subtype': 'frequent_time_trouble',
                'frequency': len(time_pressure_games),
                'severity': severity,
                'first_seen': first_seen,
                'last_seen': last_seen,
                'examples': time_pressure_games[:5],
                'recommendation': (
                    f"You frequently get into severe time trouble ({len(time_pressure_games)} games). "
                    "Consider faster opening play, longer time controls, or time management training."
                )
            })

        return patterns
