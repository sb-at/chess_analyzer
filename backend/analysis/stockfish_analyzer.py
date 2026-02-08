"""Stockfish chess engine integration for position analysis."""
import chess
import chess.engine
import chess.pgn
from typing import Dict, List, Optional
from io import StringIO
from config import get_settings

settings = get_settings()


class StockfishAnalyzer:
    """Wrapper for Stockfish chess engine analysis."""

    def __init__(self, stockfish_path: Optional[str] = None, depth: int = None):
        """Initialize Stockfish analyzer.

        Args:
            stockfish_path: Path to Stockfish executable
            depth: Analysis depth (default from settings)
        """
        self.stockfish_path = stockfish_path or settings.stockfish_path
        self.depth = depth or settings.stockfish_depth
        self.engine = None

    def __enter__(self):
        """Context manager entry - start engine."""
        self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        self.engine.configure({"Threads": settings.stockfish_threads})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - quit engine."""
        if self.engine:
            self.engine.quit()

    def analyze_position(self, fen: str, depth: Optional[int] = None) -> Dict:
        """Analyze a single chess position.

        Args:
            fen: FEN string representing the position
            depth: Analysis depth (uses instance depth if not specified)

        Returns:
            Dictionary with evaluation, best_move, and depth
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Use context manager.")

        board = chess.Board(fen)
        analysis_depth = depth or self.depth

        info = self.engine.analyse(board, chess.engine.Limit(depth=analysis_depth))

        # Extract score
        score = info.get('score')
        if score:
            # Convert to centipawns from player's perspective
            eval_cp = score.relative.score(mate_score=10000)
            evaluation = eval_cp / 100 if eval_cp is not None else 0
        else:
            evaluation = 0

        # Extract best move
        pv = info.get('pv', [])
        best_move = pv[0].uci() if pv else None

        return {
            'evaluation': evaluation,
            'best_move': best_move,
            'depth': info.get('depth', analysis_depth),
            'nodes': info.get('nodes', 0)
        }

    def analyze_game(self, pgn_string: str) -> Dict:
        """Analyze all positions in a game.

        Args:
            pgn_string: PGN notation of the game

        Returns:
            Dictionary with moves_analysis and game statistics
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Use context manager.")

        # Parse PGN
        pgn = chess.pgn.read_game(StringIO(pgn_string))
        if not pgn:
            raise ValueError("Invalid PGN string")

        board = pgn.board()
        moves_analysis = []
        move_number = 1

        # Track statistics
        total_centipawn_loss = 0
        blunders = 0
        mistakes = 0
        inaccuracies = 0

        for move in pgn.mainline_moves():
            # Get FEN before move
            fen_before = board.fen()

            # Analyze position before move
            eval_before = self.analyze_position(fen_before, depth=15)

            # Make the move
            san_move = board.san(move)
            board.push(move)

            # Get FEN after move
            fen_after = board.fen()

            # Analyze position after move
            eval_after = self.analyze_position(fen_after, depth=15)

            # Calculate evaluation swing (from moving player's perspective)
            # After making a move, we flip perspective
            eval_swing = abs(eval_before['evaluation'] + eval_after['evaluation'])

            # Classify move quality
            is_blunder = eval_swing > 2.0
            is_mistake = 1.0 < eval_swing <= 2.0
            is_inaccuracy = 0.5 < eval_swing <= 1.0

            if is_blunder:
                blunders += 1
            elif is_mistake:
                mistakes += 1
            elif is_inaccuracy:
                inaccuracies += 1

            centipawn_loss = int(eval_swing * 100)
            total_centipawn_loss += centipawn_loss

            # Calculate accuracy (100 = perfect, 0 = terrible)
            accuracy = max(0, min(100, 100 - (centipawn_loss / 3)))

            moves_analysis.append({
                'move_number': move_number,
                'move': move.uci(),
                'san': san_move,
                'fen_before': fen_before,
                'fen_after': fen_after,
                'eval_before': eval_before['evaluation'],
                'eval_after': eval_after['evaluation'],
                'best_move': eval_before['best_move'],
                'is_blunder': is_blunder,
                'is_mistake': is_mistake,
                'is_inaccuracy': is_inaccuracy,
                'centipawn_loss': centipawn_loss,
                'accuracy': accuracy
            })

            move_number += 0.5  # Half-move increment

        # Calculate average accuracy
        total_moves = len(moves_analysis)
        avg_accuracy = sum(m['accuracy'] for m in moves_analysis) / total_moves if total_moves > 0 else 0

        return {
            'moves_analysis': moves_analysis,
            'stats': {
                'total_moves': total_moves,
                'avg_accuracy': round(avg_accuracy, 2),
                'blunders': blunders,
                'mistakes': mistakes,
                'inaccuracies': inaccuracies,
                'total_centipawn_loss': total_centipawn_loss
            }
        }

    def get_tactical_motifs(self, fen: str, move: str) -> List[str]:
        """Identify tactical motifs in a position.

        Args:
            fen: Position FEN
            move: Move in UCI notation

        Returns:
            List of tactical motif names
        """
        motifs = []
        board = chess.Board(fen)
        move_obj = chess.Move.from_uci(move)

        if self._is_fork(board, move_obj):
            motifs.append('fork')
        if self._is_pin(board, move_obj):
            motifs.append('pin')
        if self._is_skewer(board, move_obj):
            motifs.append('skewer')
        if self._is_discovered_attack(board, move_obj):
            motifs.append('discovered_attack')
        if self._is_removal_of_defender(board, move_obj):
            motifs.append('removal_of_defender')

        return motifs

    def _is_fork(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a fork."""
        board_copy = board.copy()
        board_copy.push(move)

        piece = board_copy.piece_at(move.to_square)
        if not piece:
            return False

        # Get all squares attacked by the piece
        attacks = board_copy.attacks(move.to_square)

        # Count valuable pieces attacked
        valuable_attacks = 0
        for square in attacks:
            target = board_copy.piece_at(square)
            if target and target.color != piece.color:
                # King, Queen, or Rook are valuable
                if target.piece_type in [chess.KING, chess.QUEEN, chess.ROOK]:
                    valuable_attacks += 1

        return valuable_attacks >= 2

    def _is_pin(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a pin."""
        board_copy = board.copy()
        piece = board_copy.piece_at(move.from_square)

        if not piece or piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
            return False

        board_copy.push(move)

        # Look for pieces in line that can't move due to exposing higher value piece
        for square in chess.SQUARES:
            target = board_copy.piece_at(square)
            if target and target.color != piece.color:
                # Check if moving this piece would expose a more valuable piece
                if board_copy.is_pinned(target.color, square):
                    return True

        return False

    def _is_skewer(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a skewer (like reverse pin)."""
        # Simplified: check if attacking a high-value piece that's protecting lower-value piece
        return False  # TODO: Implement full skewer detection

    def _is_discovered_attack(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a discovered attack."""
        board_before = board.copy()
        board_after = board.copy()
        board_after.push(move)

        moving_color = board.turn

        # Check if moving this piece reveals an attack from another piece
        # This is complex - simplified version
        return False  # TODO: Implement full discovered attack detection

    def _is_removal_of_defender(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move removes a defender."""
        # Check if the move captures or deflects a piece that was defending something
        target = board.piece_at(move.to_square)
        return target is not None  # Simplified - needs more logic
