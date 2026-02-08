"""Pattern detection module."""
from pattern_detection.tactical import TacticalPatternDetector
from pattern_detection.opening import OpeningPatternDetector
from pattern_detection.time_management import TimeManagementDetector
from pattern_detection.aggregator import PatternAggregator

__all__ = [
    "TacticalPatternDetector",
    "OpeningPatternDetector",
    "TimeManagementDetector",
    "PatternAggregator"
]
