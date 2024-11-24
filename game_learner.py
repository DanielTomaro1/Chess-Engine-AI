import chess
import chess.pgn
import os
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PositionData:
    """Data stored for each position"""
    move: str           # The move played
    num_times_played: int  # How often this move was played
    win_score: float    # Win rate with this move
    avg_eval: float     # Average evaluation after this move
    is_book: bool       # Whether it was a book move


class GameLearner:
    def __init__(self, experience_file: str = "engine_analysis/learned_positions.json"):
        """
        Initialize the learning system.
        
        Args:
            experience_file: File to store learned positions
        """
        # Create engine_analysis directory if it doesn't exist
        base_dir = Path("engine_analysis")
        base_dir.mkdir(exist_ok=True)
        
        self.experience_file = experience_file
        self.positions: Dict[str, List[PositionData]] = defaultdict(list)
        self.load_experience()
        
    def load_experience(self):
        """Load learned positions from file."""
        if os.path.exists(self.experience_file):
            try:
                with open(self.experience_file, 'r') as f:
                    data = json.load(f)
                    for fen, moves in data.items():
                        self.positions[fen] = [
                            PositionData(**move_data) for move_data in moves
                        ]
                print(f"Loaded {len(self.positions)} learned positions")
            except Exception as e:
                print(f"Error loading experience file: {e}")
                self.positions = defaultdict(list)
        else:
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(self.experience_file), exist_ok=True)

    
    def save_experience(self):
        """Save learned positions to file."""
        try:
            data = {
                fen: [vars(move_data) for move_data in moves]
                for fen, moves in self.positions.items()
            }
            with open(self.experience_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(self.positions)} learned positions")
        except Exception as e:
            print(f"Error saving experience file: {e}")

    def learn_from_game(self, pgn_file: str):
        """
        Learn from a single PGN game.
        
        Args:
            pgn_file: Path to PGN file to learn from
        """
        try:
            with open(pgn_file) as f:
                game = chess.pgn.read_game(f)
                if game is None:
                    return
                
                # Get game result
                result = game.headers.get("Result", "*")
                white_won = result == "1-0"
                black_won = result == "0-1"
                
                board = game.board()
                for move in game.mainline_moves():
                    # Get FEN for current position (excluding move counters)
                    fen = " ".join(board.fen().split(" ")[:4])
                    
                    # Get move evaluation if available
                    eval_score = 0.0  # Default if no evaluation available
                    
                    # Update position data
                    move_str = move.uci()
                    move_data = None
                    
                    # Find or create move data
                    for existing_data in self.positions[fen]:
                        if existing_data.move == move_str:
                            move_data = existing_data
                            break
                    
                    if move_data is None:
                        move_data = PositionData(
                            move=move_str,
                            num_times_played=0,
                            win_score=0.0,
                            avg_eval=0.0,
                            is_book=False  # Will be updated if it was a book move
                        )
                        self.positions[fen].append(move_data)
                    
                    # Update statistics
                    move_data.num_times_played += 1
                    
                    # Update win score
                    if white_won and board.turn == chess.WHITE:
                        move_data.win_score += 1
                    elif black_won and board.turn == chess.BLACK:
                        move_data.win_score += 1
                    
                    # Update average evaluation
                    move_data.avg_eval = (
                        (move_data.avg_eval * (move_data.num_times_played - 1) + eval_score)
                        / move_data.num_times_played
                    )
                    
                    # Make the move
                    board.push(move)
                
                print(f"Learned from game: {game.headers.get('White', '?')} vs {game.headers.get('Black', '?')}")
                
        except Exception as e:
            print(f"Error learning from game {pgn_file}: {e}")

    def learn_from_directory(self, directory: str = "engine_analysis/pgn_games"):
        """
        Learn from all PGN files in a directory.
        
        Args:
            directory: Directory containing PGN files, defaults to engine_analysis/pgn_games
        """
        start_time = time.time()
        num_games = 0
        
        # Ensure directory exists
        directory_path = Path(directory)
        if not directory_path.exists():
            print(f"Directory {directory} does not exist")
            return
            
        for file in directory_path.glob('*.pgn'):
            self.learn_from_game(str(file))
            num_games += 1
        
        self.save_experience()
        
        elapsed = time.time() - start_time
        print(f"Learned from {num_games} games in {elapsed:.2f} seconds")

    def get_move_suggestion(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Get move suggestion based on learned experience.
        
        Args:
            board: Current board position
            
        Returns:
            Suggested move or None if no learned moves available
        """
        fen = " ".join(board.fen().split(" ")[:4])
        moves = self.positions.get(fen, [])
        
        if not moves:
            return None
            
        # Sort moves by a combination of win rate and number of times played
        def move_score(data: PositionData) -> float:
            win_rate = data.win_score / data.num_times_played if data.num_times_played > 0 else 0
            play_factor = min(data.num_times_played / 10, 1)  # Cap at 10 games
            return win_rate * play_factor + data.avg_eval / 1000
        
        moves.sort(key=move_score, reverse=True)
        
        # Try to make the best move
        for move_data in moves:
            try:
                move = chess.Move.from_uci(move_data.move)
                if move in board.legal_moves:
                    return move
            except:
                continue
        
        return None
    
    def get_statistics(self) -> dict:
        """Get learning statistics."""
        total_positions = len(self.positions)
        total_moves = 0
        for position_data in self.positions.values():
            # Assuming position_data is a list of PositionData objects
            total_moves += len(position_data)
    
        return {
            'total_positions': total_positions,
            'total_moves': total_moves,
            'games_processed': self.games_processed,
            'positions_learned': len([pos for pos in self.positions.values() if pos]),
            'average_moves_per_position': total_moves / total_positions if total_positions > 0 else 0
        }

    def get_position_stats(self, board: chess.Board) -> List[Dict]:
        """
        Get statistics for all moves in a position.
        
        Args:
            board: Current board position
            
        Returns:
            List of move statistics
        """
        fen = " ".join(board.fen().split(" ")[:4])
        moves = self.positions.get(fen, [])
        
        stats = []
        for move_data in moves:
            win_rate = move_data.win_score / move_data.num_times_played if move_data.num_times_played > 0 else 0
            stats.append({
                'move': move_data.move,
                'played': move_data.num_times_played,
                'win_rate': f"{win_rate:.1%}",
                'avg_eval': f"{move_data.avg_eval:.2f}",
                'is_book': move_data.is_book
            })
            
        return stats
