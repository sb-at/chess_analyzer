"""Chess.com API client for game import."""
import httpx
import asyncio
from typing import List, Optional
from datetime import datetime
import chess.pgn
from io import StringIO
from constants import PLATFORM_CHESS_COM


class ChessComClient:
    """Client for Chess.com Public API."""

    def __init__(self, username: str, verify_ssl: bool = False):
        self.username = username.lower()
        self.base_url = "https://api.chess.com/pub"
        self.rate_limit_delay = 0.5  # 2 requests per second max
        self.verify_ssl = verify_ssl  # Disabled by default to avoid SSL cert issues

    async def get_player_profile(self) -> dict:
        """Get player profile information."""
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.get(
                f"{self.base_url}/player/{self.username}"
            )
            response.raise_for_status()
            return response.json()

    async def get_game_archives(self) -> List[str]:
        """Get list of monthly archive URLs."""
        await asyncio.sleep(self.rate_limit_delay)
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.get(
                f"{self.base_url}/player/{self.username}/games/archives"
            )
            response.raise_for_status()
            return response.json().get("archives", [])

    async def get_games_from_archive(self, archive_url: str) -> List[dict]:
        """Fetch games from a specific monthly archive."""
        await asyncio.sleep(self.rate_limit_delay)
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.get(archive_url)
            response.raise_for_status()
            return response.json().get("games", [])

    async def import_recent_games(self, limit: int = 500) -> List[dict]:
        """Import most recent games up to limit."""
        archives = await self.get_game_archives()
        all_games = []

        # Start from most recent archive and work backwards
        for archive_url in reversed(archives):
            if len(all_games) >= limit:
                break

            month_games = await self.get_games_from_archive(archive_url)
            all_games.extend(month_games)

            # Break early if we have enough games
            if len(all_games) >= limit:
                all_games = all_games[:limit]
                break

        # Process games into standardized format
        processed_games = []
        for game in all_games:
            processed = self._process_game(game)
            if processed:
                processed_games.append(processed)

        return processed_games

    async def get_time_controls_quick(self, sample_size: int = 100) -> tuple[dict[str, int], int]:
        """Quickly scan recent games to discover time controls played.

        Args:
            sample_size: Number of games to sample

        Returns:
            Tuple of (time_controls_dict, total_sampled) where:
            - time_controls_dict: {time_control: count}
            - total_sampled: Number of games actually sampled
        """
        archives = await self.get_game_archives()
        time_controls = {}
        total_sampled = 0

        # Start from most recent archive and work backwards
        for archive_url in reversed(archives):
            if total_sampled >= sample_size:
                break

            month_games = await self.get_games_from_archive(archive_url)

            for game in month_games:
                if total_sampled >= sample_size:
                    break

                # Extract time control from game data
                time_control = game.get("time_control", "")
                if not time_control:
                    time_control = "correspondence"

                # Count this time control
                time_controls[time_control] = time_controls.get(time_control, 0) + 1
                total_sampled += 1

        return time_controls, total_sampled

    def _process_game(self, game_data: dict) -> Optional[dict]:
        """Process raw Chess.com game data into standardized format."""
        try:
            # Determine user color
            white_player = game_data.get("white", {}).get("username", "").lower()
            black_player = game_data.get("black", {}).get("username", "").lower()
            user_color = "white" if white_player == self.username else "black"

            # Parse PGN to get more details
            pgn_text = game_data.get("pgn", "")
            pgn = chess.pgn.read_game(StringIO(pgn_text))

            opening_name = None
            opening_eco = None
            if pgn:
                opening_eco = pgn.headers.get("ECO", None)
                opening_name = pgn.headers.get("Opening", None)

            # Extract time control
            time_control = game_data.get("time_control", "")
            time_class = game_data.get("time_class", "")

            return {
                "platform": PLATFORM_CHESS_COM,
                "game_id": game_data.get("url", "").split("/")[-1],
                "pgn": pgn_text,
                "date": datetime.fromtimestamp(game_data.get("end_time", 0)),
                "time_control": time_control,
                "time_class": time_class,
                "white_player": white_player,
                "black_player": black_player,
                "white_rating": game_data.get("white", {}).get("rating"),
                "black_rating": game_data.get("black", {}).get("rating"),
                "result": self._parse_result(game_data),
                "user_color": user_color,
                "opening_name": opening_name,
                "opening_eco": opening_eco,
                "url": game_data.get("url", ""),
                "analyzed": False
            }
        except Exception as e:
            print(f"Error processing game: {e}")
            return None

    def _parse_result(self, game_data: dict) -> str:
        """Parse game result from Chess.com format."""
        white_result = game_data.get("white", {}).get("result", "")
        black_result = game_data.get("black", {}).get("result", "")

        if "win" in white_result:
            return "1-0"
        elif "win" in black_result:
            return "0-1"
        elif "draw" in white_result or "draw" in black_result:
            return "1/2-1/2"
        else:
            return "*"
