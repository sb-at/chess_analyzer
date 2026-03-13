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
            'fork', 'pin', 'skewer', 'discovered_attack', 'discovered_check',
            'double_attack', 'trapped_piece', 'deflection', 'decoy',
            'removal_of_defender', 'back_rank_mate', 'hanging_piece',
            'zwischenzug', 'desperado', 'x_ray_attack'
        ]

        # Human-readable pattern descriptions
        self.pattern_descriptions = {
            # Offensive patterns (missed opportunities)
            'missed_fork': 'You missed {count} fork opportunities',
            'missed_pin': 'You missed {count} pin opportunities',
            'missed_skewer': 'You missed {count} skewer opportunities',
            'missed_discovered_attack': 'You missed {count} discovered attack opportunities',
            'missed_discovered_check': 'You missed {count} discovered check opportunities',
            'missed_double_attack': 'You missed {count} double attack opportunities',
            'missed_trapped_piece': 'You missed {count} opportunities to trap opponent pieces',
            'missed_deflection': 'You missed {count} deflection tactics',
            'missed_removal_of_defender': 'You missed {count} removal of defender tactics',
            'missed_back_rank_mate': 'You missed {count} back rank mate opportunities',
            'missed_hanging_piece': 'You missed {count} hanging pieces to capture',
            'missed_tactical_miss': 'You missed {count} tactical opportunities',
            'missed_tactical_combination': 'You missed {count} tactical combinations',

            # Defensive patterns (fell for tactics)
            'fell_for_fork': 'You fell for fork attacks {count} times',
            'fell_for_pin': 'You got pinned {count} times',
            'fell_for_skewer': 'You fell for skewer attacks {count} times',
            'fell_for_discovered_attack': 'You fell for discovered attacks {count} times',
            'fell_for_discovered_check': 'You fell for discovered check attacks {count} times',
            'fell_for_double_attack': 'You fell for double attacks {count} times',
            'fell_for_trapped_piece': 'Your pieces got trapped {count} times',
            'fell_for_back_rank_mate': 'You fell for back rank threats {count} times',
            'left_piece_hanging': 'You left pieces hanging {count} times',
            'fell_for_tactical': 'You fell for tactical threats {count} times'
        }

    def detect(self, games: List[Dict]) -> List[Dict]:
        """Detect tactical patterns across games.

        Args:
            games: List of analyzed games

        Returns:
            List of detected tactical patterns
        """
        all_patterns = []

        # Collect offensive patterns (missed opportunities)
        missed_tactics = self._collect_missed_tactics(games)
        missed_patterns = self._aggregate_patterns(missed_tactics, pattern_prefix='missed_')

        # Collect defensive patterns (fell for opponent tactics)
        defensive_mistakes = self._collect_defensive_mistakes(games)
        defensive_patterns = self._aggregate_patterns(defensive_mistakes, pattern_prefix='fell_for_')

        # Combine all patterns
        all_patterns = missed_patterns + defensive_patterns

        return all_patterns

    def _collect_missed_tactics(self, games: List[Dict]) -> List[Dict]:
        """Collect all missed tactical opportunities from games."""
        mistakes = []

        for game in games:
            if not game.get('analyzed'):
                continue

            game_id = game.get('_id') or game.get('game_id')
            moves = game.get('moves', [])
            username = game.get('username', '').lower()
            white_player = game.get('white', {}).get('username', '').lower()

            for move_data in moves:
                # Determine if this is the user's move.
                # move_number is stored as integers for white (1, 2, 3...)
                # and as n.5 for black (1.5, 2.5, 3.5...).
                move_num = move_data.get('move_number', 0)
                is_white_move = (move_num % 1) == 0
                is_user_move = (is_white_move and username == white_player) or \
                               (not is_white_move and username != white_player)

                # Only track missed tactics on user's own moves
                if not is_user_move:
                    continue

                # Look for significant eval swings (missed tactics)
                if move_data.get('is_blunder') or move_data.get('is_mistake'):
                    # Identify tactical motif if possible
                    motif = self._identify_missed_tactic_motif(
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

    def _collect_defensive_mistakes(self, games: List[Dict]) -> List[Dict]:
        """Collect instances where user's move allowed the opponent to gain a significant advantage.

        Stores the user's position (fen_before) and the best defensive move the user
        should have played, so the viewer shows what white/black should have done
        differently — not the opponent's subsequent tactic.
        """
        defensive_errors = []

        for game in games:
            if not game.get('analyzed'):
                continue

            game_id = game.get('_id') or game.get('game_id')
            moves = game.get('moves', [])
            username = game.get('username', '').lower()
            white_player = game.get('white', {}).get('username', '').lower()

            for i, move_data in enumerate(moves):
                if i + 1 >= len(moves):
                    continue

                # Only look at analyzed moves (opening moves have no eval data)
                if not move_data.get('analyzed'):
                    continue

                next_move = moves[i + 1]

                # Determine if current move is user's move
                move_num = move_data.get('move_number', 0)
                is_white_move = (move_num % 1) == 0
                is_user_move = (is_white_move and username == white_player) or \
                               (not is_white_move and username != white_player)

                if not is_user_move:
                    continue

                # Skip moves already flagged as blunders/mistakes — those are covered
                # by _collect_missed_tactics to avoid double-counting
                if move_data.get('is_blunder') or move_data.get('is_mistake'):
                    continue

                # Opponent's eval_before (from their perspective) tells us how good their
                # position is after the user's move.  Values are in pawns.
                next_eval_before = next_move.get('eval_before')
                if next_eval_before is None:
                    continue

                # If opponent has > 1.5 pawn advantage and didn't blunder it away,
                # the user's move left a vulnerable position
                if next_eval_before < 1.5:
                    continue

                if next_move.get('is_blunder'):
                    continue

                # If the user already played the best defensive move, don't flag it —
                # the position was simply bad regardless
                best_move = move_data.get('best_move')
                played_move = move_data.get('move')
                if best_move and played_move and best_move[:4] == played_move[:4]:
                    continue

                # Identify what tactic the opponent could use
                motif = self._identify_defensive_weakness_motif(
                    move_data.get('fen_after', ''),
                    next_move.get('move', ''),
                    move_data.get('move', '')
                )

                defensive_errors.append({
                    'game_id': game_id,
                    'move_number': move_data.get('move_number'),
                    # Store USER's position so the board shows the user's turn
                    'fen': move_data.get('fen_before'),
                    'missed_move': move_data.get('best_move'),  # best defensive move for user
                    'played_move': move_data.get('move'),
                    'san': move_data.get('san'),  # user's actual move
                    'eval_loss': int(next_eval_before * 100),
                    'motif': motif,
                    'is_mistake': True,
                    'date': game.get('date')
                })

        return defensive_errors

    def _identify_missed_tactic_motif(
        self,
        fen: str,
        best_move: str,
        played_move: str
    ) -> Optional[str]:
        """Identify the tactical motif the user missed.

        Args:
            fen: Position FEN
            best_move: Best move in UCI notation
            played_move: Move that was played

        Returns:
            Name of tactical motif or None
        """
        if not fen or not best_move:
            return 'tactical_miss'

        try:
            board = chess.Board(fen)
            move = chess.Move.from_uci(best_move)

            # Check for various tactical motifs in priority order
            if self._is_back_rank_mate(board, move):
                return 'back_rank_mate'
            if self._is_fork_position(board, move):
                return 'fork'
            if self._is_discovered_check(board, move):
                return 'discovered_check'
            if self._is_discovered_attack(board, move):
                return 'discovered_attack'
            if self._is_skewer_position(board, move):
                return 'skewer'
            if self._is_pin_position(board, move):
                return 'pin'
            if self._is_removal_of_defender(board, move):
                return 'removal_of_defender'
            if self._is_trapped_piece_tactic(board, move):
                return 'trapped_piece'
            if played_move and self._is_hanging_piece(board, played_move):
                return 'hanging_piece'
            if self._is_tactical_blow(board, move):
                return 'tactical_combination'

            # Default to generic tactical miss
            return 'tactical_miss'

        except Exception as e:
            print(f"Error identifying missed tactic motif: {e}")
            return 'tactical_miss'

    def _identify_defensive_weakness_motif(
        self,
        fen: str,
        opponent_move: str,
        user_move: str
    ) -> Optional[str]:
        """Identify what tactical weakness the opponent exploited.

        Args:
            fen: Position FEN after user's move
            opponent_move: Opponent's move that punished user
            user_move: User's move that created the weakness

        Returns:
            Name of defensive weakness
        """
        if not fen or not opponent_move:
            return 'tactical'

        try:
            board = chess.Board(fen)
            opp_move = chess.Move.from_uci(opponent_move)

            # Check what tactic opponent used
            if self._is_fork_position(board, opp_move):
                return 'fork'
            if self._is_discovered_check(board, opp_move):
                return 'discovered_check'
            if self._is_discovered_attack(board, opp_move):
                return 'discovered_attack'
            if self._is_skewer_position(board, opp_move):
                return 'skewer'
            if self._is_pin_position(board, opp_move):
                return 'pin'
            if self._is_back_rank_mate(board, opp_move):
                return 'back_rank_mate'
            if user_move and self._is_hanging_piece(board, user_move):
                return 'hanging'
            if self._is_double_attack(board, opp_move):
                return 'double_attack'
            if self._is_trapped_piece_tactic(board, opp_move):
                return 'trapped_piece'

            return 'tactical'

        except Exception as e:
            print(f"Error identifying defensive weakness: {e}")
            return 'tactical'

    def _is_fork_position(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a fork (any piece type attacking 2+ more-valuable enemies)."""
        PIECE_VALUES = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 100,
        }
        try:
            board_copy = board.copy()
            board_copy.push(move)

            piece = board_copy.piece_at(move.to_square)
            if not piece:
                return False

            attacker_value = PIECE_VALUES.get(piece.piece_type, 0)
            forked = 0

            for square in board_copy.attacks(move.to_square):
                target = board_copy.piece_at(square)
                if target and target.color != piece.color:
                    target_value = PIECE_VALUES.get(target.piece_type, 0)
                    # Target must be worth more than the attacker so the trade is
                    # profitable for whichever target the opponent chooses to save.
                    if target_value > attacker_value or target.piece_type == chess.KING:
                        forked += 1

            return forked >= 2
        except:
            return False

    def _is_pin_position(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a NEW pin that did not exist before."""
        try:
            piece = board.piece_at(move.from_square)
            if not piece:
                return False

            # Only sliders can create pins
            if piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                return False

            enemy_color = not piece.color

            # Record which enemy squares are already pinned before the move
            pinned_before = {
                sq for sq in chess.SQUARES
                if board.is_pinned(enemy_color, sq) and board.piece_at(sq)
            }

            board_copy = board.copy()
            board_copy.push(move)

            # A new pin exists if an enemy piece is pinned after the move
            # but was not pinned before
            for sq in chess.SQUARES:
                if sq not in pinned_before and board_copy.is_pinned(enemy_color, sq) and board_copy.piece_at(sq):
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

    def _is_discovered_check(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a discovered check."""
        try:
            piece = board.piece_at(move.from_square)
            if not piece:
                return False

            # Make the move
            board_copy = board.copy()
            board_copy.push(move)

            # Check if opponent is in check and the piece that moved is not giving check
            if board_copy.is_check():
                # Find if check is from a piece other than the one that moved
                checkers = board_copy.checkers()
                if move.to_square not in checkers:
                    return True

            return False
        except:
            return False

    def _is_discovered_attack(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a discovered attack (not check)."""
        try:
            piece = board.piece_at(move.from_square)
            if not piece:
                return False

            board_copy = board.copy()
            board_copy.push(move)

            # Look for pieces on the line of the move that now attack valuable targets
            enemy_color = not piece.color

            # Check if any friendly piece behind the moved piece now attacks something valuable
            for square in chess.SQUARES:
                attacker = board_copy.piece_at(square)
                if attacker and attacker.color == piece.color and square != move.to_square:
                    if attacker.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                        attacks = board_copy.attacks(square)
                        for target_square in attacks:
                            target = board_copy.piece_at(target_square)
                            if target and target.color == enemy_color:
                                if target.piece_type in [chess.QUEEN, chess.ROOK]:
                                    # Check if this attack wasn't possible before the move
                                    if not board.attacks(square) or target_square not in board.attacks(square):
                                        return True

            return False
        except:
            return False

    def _is_skewer_position(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a skewer (attacking through a valuable piece to another)."""
        try:
            piece = board.piece_at(move.from_square)
            if not piece or piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                return False

            board_copy = board.copy()
            board_copy.push(move)
            enemy_color = not piece.color
            attacker_sq = move.to_square

            for attacked_sq in board_copy.attacks(attacker_sq):
                attacked_piece = board_copy.piece_at(attacked_sq)
                if not attacked_piece or attacked_piece.color != enemy_color:
                    continue
                if attacked_piece.piece_type not in [chess.QUEEN, chess.ROOK, chess.KING]:
                    continue

                # Use the ray bitboard to find pieces further along the same line.
                # A square is "beyond" attacked_sq when attacked_sq lies between
                # attacker_sq and that square.
                ray_mask = chess.BB_RAYS[attacker_sq][attacked_sq]
                for beyond_sq in chess.SquareSet(ray_mask):
                    if beyond_sq == attacker_sq or beyond_sq == attacked_sq:
                        continue
                    # Skip squares that are on the attacker's side of attacked_sq
                    if not (chess.BB_SQUARES[attacked_sq] & chess.BB_BETWEEN[attacker_sq][beyond_sq]):
                        continue
                    beyond_piece = board_copy.piece_at(beyond_sq)
                    if beyond_piece and beyond_piece.color == enemy_color:
                        return True

            return False
        except:
            return False

    def _is_back_rank_mate(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move creates a back rank mate threat or delivers mate."""
        try:
            board_copy = board.copy()
            board_copy.push(move)

            # Check if it's mate
            if board_copy.is_checkmate():
                # Check if king is on back rank
                enemy_king_square = board_copy.king(not board.turn)
                if enemy_king_square:
                    rank = chess.square_rank(enemy_king_square)
                    if rank == 0 or rank == 7:
                        return True

            return False
        except:
            return False

    def _is_removal_of_defender(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move removes a defender of a valuable piece."""
        try:
            # Check if the move captures or deflects a defending piece
            target = board.piece_at(move.to_square)
            if not target:
                return False

            board_copy = board.copy()

            # Before the move, check what the captured piece was defending
            defending = []
            for square in chess.SQUARES:
                piece = board_copy.piece_at(square)
                if piece and piece.color == target.color:
                    if board_copy.is_attacked_by(target.color, square):
                        if piece.piece_type in [chess.QUEEN, chess.ROOK]:
                            defending.append(square)

            # After the move, check if those pieces are now undefended
            board_copy.push(move)
            for defended_square in defending:
                if not board_copy.is_attacked_by(target.color, defended_square):
                    return True

            return False
        except:
            return False

    def _is_trapped_piece_tactic(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move traps an opponent's piece."""
        try:
            board_copy = board.copy()
            board_copy.push(move)

            enemy_color = not board.turn

            # Check if any enemy piece has no safe squares
            for square in chess.SQUARES:
                piece = board_copy.piece_at(square)
                if piece and piece.color == enemy_color:
                    if piece.piece_type in [chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP]:
                        # Check if piece has any safe moves
                        has_safe_move = False
                        for legal_move in board_copy.legal_moves:
                            if legal_move.from_square == square:
                                temp_board = board_copy.copy()
                                temp_board.push(legal_move)
                                if not temp_board.is_attacked_by(not enemy_color, legal_move.to_square):
                                    has_safe_move = True
                                    break

                        if not has_safe_move and board_copy.is_attacked_by(not enemy_color, square):
                            return True

            return False
        except:
            return False

    def _is_double_attack(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move attacks two pieces simultaneously."""
        try:
            board_copy = board.copy()
            board_copy.push(move)

            attacks = board_copy.attacks(move.to_square)
            enemy_color = not board.turn
            valuable_attacks = 0

            for square in attacks:
                target = board_copy.piece_at(square)
                if target and target.color == enemy_color:
                    if target.piece_type in [chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP]:
                        valuable_attacks += 1

            return valuable_attacks >= 2
        except:
            return False

    def _aggregate_patterns(self, mistakes: List[Dict], pattern_prefix: str = 'missed_') -> List[Dict]:
        """Group similar tactical patterns together.

        Args:
            mistakes: List of tactical mistakes/errors
            pattern_prefix: Prefix for pattern keys ('missed_' or 'fell_for_')

        Returns:
            List of aggregated patterns with human-readable descriptions
        """
        grouped = defaultdict(list)

        for mistake in mistakes:
            motif = mistake.get('motif', 'unknown')
            key = f"{pattern_prefix}{motif}"
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

            # Get human-readable description
            description = self._get_human_readable_description(pattern_key, len(examples))

            result.append({
                'pattern_type': 'tactical',
                'pattern_subtype': pattern_key,
                'description': description,  # Add human-readable description
                'frequency': len(examples),
                'severity': severity,
                'avg_eval_loss': round(avg_eval_loss, 1),
                'examples': examples[:5],  # Keep top 5 examples
                'first_seen': first_seen,
                'last_seen': last_seen,
                'recommendation': self._get_recommendation(pattern_key, len(examples), severity),
                'metadata': {
                    'pattern_category': 'offensive' if pattern_prefix == 'missed_' else 'defensive',
                    'avg_eval_loss': round(avg_eval_loss, 1)
                }
            })

        # Sort by impact (severity × frequency)
        return sorted(result, key=lambda x: x['severity'] * x['frequency'], reverse=True)

    def _get_human_readable_description(self, pattern_key: str, count: int) -> str:
        """Get human-readable description for a pattern.

        Args:
            pattern_key: Pattern identifier (e.g., 'missed_fork', 'fell_for_pin')
            count: Frequency count

        Returns:
            Human-readable description
        """
        template = self.pattern_descriptions.get(pattern_key)
        if template:
            return template.format(count=count)

        # Fallback: Create generic description from pattern key
        parts = pattern_key.split('_')
        if len(parts) >= 2:
            action = ' '.join(parts[:-1])
            motif = parts[-1].replace('_', ' ')
            return f"{action.capitalize()} {motif} {count} times"

        return f"{pattern_key} ({count} times)"

    def _get_recommendation(self, pattern_key: str, frequency: int, severity: float) -> str:
        """Generate recommendation based on pattern."""
        # Determine urgency level
        if severity > 0.7:
            urgency = "Critical"
        elif severity > 0.4:
            urgency = "Important"
        else:
            urgency = "Moderate"

        # Check if it's offensive (missed) or defensive (fell for) pattern
        if pattern_key.startswith('missed_'):
            motif = pattern_key.replace('missed_', '').replace('_', ' ')
            return (
                f"{urgency}: You're missing {motif} tactics frequently ({frequency} times). "
                f"Practice {motif} puzzles to sharpen your tactical vision."
            )
        elif pattern_key.startswith('fell_for_'):
            motif = pattern_key.replace('fell_for_', '').replace('_', ' ')
            return (
                f"{urgency}: You're vulnerable to {motif} attacks ({frequency} times). "
                f"Study defensive techniques and be more alert to {motif} threats."
            )
        elif pattern_key.startswith('left_piece_'):
            return (
                f"{urgency}: You're leaving pieces undefended too often ({frequency} times). "
                "Always check if your pieces are protected before moving."
            )
        else:
            motif = pattern_key.replace('_', ' ')
            return (
                f"{urgency}: Pattern detected: {motif} ({frequency} occurrences). "
                "Review these positions to improve."
            )
