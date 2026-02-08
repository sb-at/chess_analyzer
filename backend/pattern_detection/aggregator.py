"""Pattern aggregation and analysis orchestration."""
from typing import List, Dict
from datetime import datetime
from pattern_detection.tactical import TacticalPatternDetector
from pattern_detection.opening import OpeningPatternDetector
from pattern_detection.time_management import TimeManagementDetector


class PatternAggregator:
    """Aggregates results from all pattern detectors."""

    def __init__(self):
        """Initialize pattern aggregator with all detectors."""
        self.detectors = {
            'tactical': TacticalPatternDetector(),
            'opening': OpeningPatternDetector(),
            'time_management': TimeManagementDetector()
        }

    async def analyze_user_games(self, games: List[Dict]) -> Dict:
        """Run all pattern detectors and aggregate results.

        Args:
            games: List of analyzed games

        Returns:
            Aggregated analysis results with patterns and statistics
        """
        if len(games) < 5:
            return {
                'error': 'Insufficient games for pattern analysis',
                'games_count': len(games),
                'minimum_required': 5
            }

        # Run all detectors
        all_patterns = []

        for detector_name, detector in self.detectors.items():
            try:
                patterns = detector.detect(games)
                all_patterns.extend(patterns)
            except Exception as e:
                print(f"Error in {detector_name} detector: {e}")

        # Sort by impact (severity × frequency)
        prioritized = sorted(
            all_patterns,
            key=lambda p: p.get('severity', 0) * p.get('frequency', 0),
            reverse=True
        )

        # Calculate overall statistics
        stats = self._calculate_overall_stats(games, all_patterns)

        return {
            'top_3_blindspots': prioritized[:3],
            'all_patterns': prioritized,
            'total_patterns': len(prioritized),
            'analyzed_games_count': len(games),
            'stats': stats,
            'analyzed_at': datetime.utcnow().isoformat()
        }

    def _calculate_overall_stats(self, games: List[Dict], patterns: List[Dict]) -> Dict:
        """Calculate overall statistics across all games.

        Args:
            games: List of analyzed games
            patterns: List of detected patterns

        Returns:
            Overall statistics dictionary
        """
        analyzed_games = [g for g in games if g.get('analyzed')]

        if not analyzed_games:
            return {
                'total_games': len(games),
                'analyzed_games': 0
            }

        # Aggregate statistics
        total_moves = 0
        total_blunders = 0
        total_mistakes = 0
        total_inaccuracies = 0
        total_accuracy = 0

        for game in analyzed_games:
            stats = game.get('stats', {})
            total_moves += stats.get('total_moves', 0)
            total_blunders += stats.get('blunders', 0)
            total_mistakes += stats.get('mistakes', 0)
            total_inaccuracies += stats.get('inaccuracies', 0)
            total_accuracy += stats.get('avg_accuracy', 0)

        avg_accuracy = total_accuracy / len(analyzed_games) if analyzed_games else 0

        # Pattern breakdown by type
        pattern_breakdown = {}
        for pattern in patterns:
            pattern_type = pattern.get('pattern_type', 'unknown')
            if pattern_type not in pattern_breakdown:
                pattern_breakdown[pattern_type] = {
                    'count': 0,
                    'total_severity': 0
                }
            pattern_breakdown[pattern_type]['count'] += 1
            pattern_breakdown[pattern_type]['total_severity'] += pattern.get('severity', 0)

        return {
            'total_games': len(games),
            'analyzed_games': len(analyzed_games),
            'total_moves': total_moves,
            'total_blunders': total_blunders,
            'total_mistakes': total_mistakes,
            'total_inaccuracies': total_inaccuracies,
            'avg_accuracy': round(avg_accuracy, 2),
            'blunder_rate': round(total_blunders / total_moves * 100, 2) if total_moves > 0 else 0,
            'mistake_rate': round(total_mistakes / total_moves * 100, 2) if total_moves > 0 else 0,
            'pattern_breakdown': pattern_breakdown
        }

    def generate_recommendations(self, patterns: List[Dict], limit: int = 5) -> List[str]:
        """Generate prioritized recommendations based on patterns.

        Args:
            patterns: List of detected patterns
            limit: Maximum number of recommendations

        Returns:
            List of recommendation strings
        """
        # Sort patterns by impact
        sorted_patterns = sorted(
            patterns,
            key=lambda p: p.get('severity', 0) * p.get('frequency', 0),
            reverse=True
        )

        recommendations = []

        for pattern in sorted_patterns[:limit]:
            rec = pattern.get('recommendation')
            if rec:
                recommendations.append(rec)

        return recommendations
