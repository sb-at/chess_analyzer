"""Tactical pattern detection engine."""
from typing import List, Dict, Optional
from collections import defaultdict
import chess
import chess.pgn
from datetime import datetime


class TacticalPatternDetector:
    """Detector for tactical patterns and missed opportunities."""

    def __init__(self):
        """Initialize tactical pattern detector."""
        self.tactical_motifs = [
            'fork', 'pin', 'skewer', 'discovered_attack',
            'double_attack', 'trapped_piece', 'deflection',
            'decoy', 'removal_of_defender'
        ]

    def detect(self, games: List[Dict]) -> List[Dict]:
        """Detect tactical patterns across games.

        Args:
            games: List of analyzed games

        Returns:
            List of detected tactical patterns
        """
        all_patterns = []

        # Collect all tactical mistakes
        tactical_mistakes = self._collect_tactical_mistakes(games)

        # Aggregate and identify patterns
        patterns = self._aggregate_patterns(tactical_mistakes)

        return patterns

    def _collect_tactical_mistakes(self, games: List[Dict]) -> List[Dict]:
        """Collect all tactical mistakes from games."""
        mistakes = []

        for game in games:
            if not game.get('analyzed'):
                continue

            game_id = game.get('_id') or game.get('game_id')
            moves = game.get('moves', [])

            for move_data in moves:
                # Look for significant eval swings (missed tactics)
                if move_data.get('is_blunder') or move_data.get('is_mistake'):
                    # Identify tactical motif if possible
                    motif = self._identify_tactical_motif(
                        move_data.get('fen_before', ''),
                        move_data.get('best_move', ''),
                        move_data.get('move', '')
                    )

                    mistakes.append({
                        'game_id': game_id,
                        'move_number': move_data.get('move_number'),
                        'fen': move_data.get('fen_before'),
                        'missed_move': move_data.get('best_move'),
                        'played_move': move_data.get('move'),
                        'san': move_data.get('san'),
                        'eval_loss': move_data.get('centipawn_loss', 0),
                        'motif': motif,
                        'is_blunder': move_data.get('is_blunder', False),
                        'date': game.get('date')
                    })

        return mistakes

    def _identify_tactical_motif(
        self,
        fen: str,
        best_move: str,
        played_move: str
    ) -> Optional[str]:
        """Identify the tactical motif in a position.

        Args:
            fen: Position FEN
            best_move: Best move in UCI notation
            played_move: Move that was played

        Returns:
            Name of tactical motif or None
        """
        if not fen or not best_move:
            return None

        try:
            board = chess.Board(fen)
            move = chess.Move.from_uci(best_move)

            # Simple heuristics for common motifs
            if self._is_fork_position(board, move):
                return 'fork'
            if self._is_pin_position(board, move):
                return 'pin'
            if self._is_hanging_piece(board, played_move):
                return 'hanging_piece'
            if self._is_tactical_blow(board, move):
                return 'tactical_combination'

            # Default to generic tactical miss
            return 'tactical_miss'

        except Exception as e:
            print(f"Error identifying motif: {e}")
            return 'tactical_miss'

    def _is_fork_position(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a fork."""
        try:
            board_copy = board.copy()
            board_copy.push(move)

            piece = board_copy.piece_at(move.to_square)
            if not piece:
                return False

            # Knights are classic forking pieces
            if piece.piece_type == chess.KNIGHT:
                attacks = board_copy.attacks(move.to_square)
                valuable_attacks = 0

                for square in attacks:
                    target = board_copy.piece_at(square)
                    if target and target.color != piece.color:
                        if target.piece_type in [chess.QUEEN, chess.ROOK, chess.KING]:
                            valuable_attacks += 1

                return valuable_attacks >= 2

            return False
        except:
            return False

    def _is_pin_position(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if position involves a pin."""
        try:
            piece = board.piece_at(move.from_square)
            if not piece:
                return False

            # Bishops, rooks, and queens can create pins
            if piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                board_copy = board.copy()
                board_copy.push(move)

                # Check if any enemy piece is now pinned
                enemy_color = not piece.color
                for square in chess.SQUARES:
                    if board_copy.is_pinned(enemy_color, square):
                        return True

            return False
        except:
            return False

    def _is_hanging_piece(self, board: chess.Board, played_move: str) -> bool:
        """Check if a piece was left hanging."""
        try:
            if not played_move:
                return False

            move = chess.Move.from_uci(played_move)
            board_copy = board.copy()
            board_copy.push(move)

            # Check if the piece that just moved is now attacked and not defended
            piece = board_copy.piece_at(move.to_square)
            if not piece:
                return False

            is_attacked = board_copy.is_attacked_by(not piece.color, move.to_square)
            is_defended = board_copy.is_attacked_by(piece.color, move.to_square)

            return is_attacked and not is_defended

        except:
            return False

    def _is_tactical_blow(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move is a strong tactical blow (capture of valuable piece)."""
        try:
            target = board.piece_at(move.to_square)
            if target and target.piece_type in [chess.QUEEN, chess.ROOK]:
                return True
            return False
        except:
            return False

    def _aggregate_patterns(self, mistakes: List[Dict]) -> List[Dict]:
        """Group similar tactical patterns together."""
        grouped = defaultdict(list)

        for mistake in mistakes:
            motif = mistake.get('motif', 'unknown')
            key = f"missed_{motif}"
            grouped[key].append(mistake)

        result = []

        for pattern_key, examples in grouped.items():
            if len(examples) < 2:  # Minimum frequency threshold
                continue

            # Calculate severity based on eval loss and frequency
            avg_eval_loss = sum(ex['eval_loss'] for ex in examples) / len(examples)
            severity = min(1.0, avg_eval_loss / 300)  # Normalize to 0-1

            # Get date range
            dates = [ex['date'] for ex in examples if ex.get('date')]
            first_seen = min(dates) if dates else None
            last_seen = max(dates) if dates else None

            result.append({
                'pattern_type': 'tactical',
                'pattern_subtype': pattern_key,
                'frequency': len(examples),
                'severity': severity,
                'avg_eval_loss': round(avg_eval_loss, 1),
                'examples': examples[:5],  # Keep top 5 examples
                'first_seen': first_seen,
                'last_seen': last_seen,
                'recommendation': self._get_recommendation(pattern_key, len(examples), severity)
            })

        # Sort by impact (severity × frequency)
        return sorted(result, key=lambda x: x['severity'] * x['frequency'], reverse=True)

    def _get_recommendation(self, pattern_key: str, frequency: int, severity: float) -> str:
        """Generate recommendation based on pattern."""
        motif = pattern_key.replace('missed_', '').replace('_', ' ')

        if severity > 0.7:
            urgency = "Critical"
        elif severity > 0.4:
            urgency = "Important"
        else:
            urgency = "Moderate"

        return (
            f"{urgency}: You're missing {motif} tactics in {frequency} games. "
            f"Practice {motif} puzzles to improve your tactical vision."
        )
