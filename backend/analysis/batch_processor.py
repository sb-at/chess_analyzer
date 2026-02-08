"""Batch processing for analyzing multiple games efficiently."""
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Optional
import json
from datetime import datetime
from analysis.stockfish_analyzer import StockfishAnalyzer
from config import get_settings

settings = get_settings()


class BatchGameAnalyzer:
    """Batch analyzer for processing multiple games efficiently."""

    def __init__(self, num_workers: int = None, use_cache: bool = True):
        """Initialize batch analyzer.

        Args:
            num_workers: Number of parallel workers (default: CPU count)
            use_cache: Whether to use Redis cache for results
        """
        self.num_workers = num_workers or settings.stockfish_threads
        self.use_cache = use_cache
        self.cache = None

        if use_cache:
            try:
                import redis
                self.cache = redis.Redis.from_url(settings.redis_url)
            except ImportError:
                print("Redis not available, caching disabled")
                self.use_cache = False

    def analyze_games_batch(self, games: List[Dict]) -> List[Dict]:
        """Analyze multiple games in parallel using process pool.

        Args:
            games: List of game dictionaries with 'pgn' and 'game_id'

        Returns:
            List of analyzed games with moves_analysis and stats
        """
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(executor.map(self._analyze_single_game, games))

        return results

    async def analyze_games_batch_async(self, games: List[Dict]) -> List[Dict]:
        """Async version of batch game analysis.

        Args:
            games: List of game dictionaries

        Returns:
            List of analyzed games
        """
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            tasks = [
                loop.run_in_executor(executor, self._analyze_single_game, game)
                for game in games
            ]
            results = await asyncio.gather(*tasks)

        return results

    def _analyze_single_game(self, game: Dict) -> Dict:
        """Analyze a single game with caching.

        Args:
            game: Game dictionary with 'pgn' and 'game_id'

        Returns:
            Analyzed game with moves_analysis and stats
        """
        game_id = game.get('game_id')

        # Check cache first
        if self.use_cache and game_id:
            cached = self._get_cached_analysis(game_id)
            if cached:
                return {**game, **cached}

        # Analyze with Stockfish
        pgn = game.get('pgn', '')

        if not pgn:
            return {
                **game,
                'analyzed': False,
                'error': 'No PGN provided'
            }

        try:
            with StockfishAnalyzer() as analyzer:
                analysis = analyzer.analyze_game(pgn)

            result = {
                **game,
                'moves': analysis['moves_analysis'],
                'stats': analysis['stats'],
                'analyzed': True,
                'analyzed_at': datetime.utcnow()
            }

            # Cache result
            if self.use_cache and game_id:
                self._cache_analysis(game_id, analysis)

            return result

        except Exception as e:
            print(f"Error analyzing game {game_id}: {e}")
            return {
                **game,
                'analyzed': False,
                'error': str(e)
            }

    def _get_cached_analysis(self, game_id: str) -> Optional[Dict]:
        """Get cached analysis from Redis.

        Args:
            game_id: Game identifier

        Returns:
            Cached analysis or None
        """
        if not self.cache:
            return None

        try:
            cached = self.cache.get(f"analysis:{game_id}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Cache retrieval error: {e}")

        return None

    def _cache_analysis(self, game_id: str, analysis: Dict):
        """Cache analysis result in Redis.

        Args:
            game_id: Game identifier
            analysis: Analysis result to cache
        """
        if not self.cache:
            return

        try:
            # Convert datetime objects to strings for JSON serialization
            analysis_copy = self._serialize_for_cache(analysis)

            # Cache for 7 days
            self.cache.setex(
                f"analysis:{game_id}",
                7 * 24 * 3600,
                json.dumps(analysis_copy)
            )
        except Exception as e:
            print(f"Cache storage error: {e}")

    def _serialize_for_cache(self, data: any) -> any:
        """Recursively serialize data for caching."""
        if isinstance(data, dict):
            return {k: self._serialize_for_cache(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_cache(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
