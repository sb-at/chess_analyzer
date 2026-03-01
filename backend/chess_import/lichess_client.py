"""Lichess API client for game import."""
import httpx
from typing import AsyncIterator, List, Optional
from datetime import datetime
import json
import chess.pgn
from io import StringIO


class LichessClient:
    """Client for Lichess API."""

    def __init__(self, username: str, token: Optional[str] = None):
        self.username = username.lower()
        self.token = token
        self.base_url = "https://lichess.org/api"

    async def get_user_profile(self) -> dict:
        """Get user profile information."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(
                f"{self.base_url}/user/{self.username}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def stream_games(self, max_games: int = 500) -> AsyncIterator[dict]:
        """Stream games using NDJSON API."""
        headers = {"Accept": "application/x-ndjson"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        params = {
            "max": max_games,
            "pgnInJson": "true",
            "clocks": "true",
            "evals": "false",
            "opening": "true"
        }

        async with httpx.AsyncClient(timeout=300.0, verify=False) as client:
            async with client.stream(
                "GET",
                f"{self.base_url}/games/user/{self.username}",
                params=params,
                headers=headers
            ) as response:
                response.raise_for_status()
                count = 0

                async for line in response.aiter_lines():
                    if line.strip() and count < max_games:
                        try:
                            game_data = json.loads(line)
                            yield game_data
                            count += 1
                        except json.JSONDecodeError:
                            continue

    async def import_recent_games(self, limit: int = 500) -> List[dict]:
        """Import most recent games up to limit."""
        games = []

        async for game_data in self.stream_games(max_games=limit):
            processed = self._process_game(game_data)
            if processed:
                games.append(processed)

        return games

    async def get_time_controls_quick(self, sample_size: int = 100) -> tuple[dict[str, int], int]:
        """Quickly scan recent games to discover time controls played.

        Args:
            sample_size: Number of games to sample

        Returns:
            Tuple of (time_controls_dict, total_sampled) where:
            - time_controls_dict: {time_control: count}
            - total_sampled: Number of games actually sampled
        """
        time_controls = {}
        total_sampled = 0

        async for game_data in self.stream_games(max_games=sample_size):
            # Extract time control without full game processing
            clock = game_data.get("clock", {})
            if clock:
                initial = clock.get("initial", 0) // 60  # Convert seconds to minutes
                increment = clock.get("increment", 0)
                time_control = f"{initial}+{increment}"
            else:
                time_control = "correspondence"

            # Count this time control
            time_controls[time_control] = time_controls.get(time_control, 0) + 1
            total_sampled += 1

        return time_controls, total_sampled

    def _process_game(self, game_data: dict) -> Optional[dict]:
        """Process raw Lichess game data into standardized format."""
        try:
            # Determine user color
            white_player = game_data.get("players", {}).get("white", {}).get("user", {}).get("name", "").lower()
            black_player = game_data.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
            user_color = "white" if white_player == self.username else "black"

            # Get PGN
            pgn_text = game_data.get("pgn", "")

            # Parse opening info
            opening = game_data.get("opening", {})
            opening_name = opening.get("name")
            opening_eco = opening.get("eco")

            # Parse timestamp
            created_at = game_data.get("createdAt", 0)
            if created_at:
                date = datetime.fromtimestamp(created_at / 1000)  # Lichess uses milliseconds
            else:
                date = datetime.utcnow()

            # Get ratings
            white_rating = game_data.get("players", {}).get("white", {}).get("rating")
            black_rating = game_data.get("players", {}).get("black", {}).get("rating")

            # Get time control
            clock = game_data.get("clock", {})
            if clock:
                initial = clock.get("initial", 0) // 60  # Convert seconds to minutes
                increment = clock.get("increment", 0)
                time_control = f"{initial}+{increment}"
            else:
                time_control = "correspondence"

            # Get result
            winner = game_data.get("winner")
            if winner == "white":
                result = "1-0"
            elif winner == "black":
                result = "0-1"
            else:
                result = "1/2-1/2"

            return {
                "platform": "lichess",
                "game_id": game_data.get("id", ""),
                "pgn": pgn_text,
                "date": date,
                "time_control": time_control,
                "white_player": white_player,
                "black_player": black_player,
                "white_rating": white_rating,
                "black_rating": black_rating,
                "result": result,
                "user_color": user_color,
                "opening_name": opening_name,
                "opening_eco": opening_eco,
                "url": f"https://lichess.org/{game_data.get('id', '')}",
                "analyzed": False
            }
        except Exception as e:
            print(f"Error processing game: {e}")
            return None
