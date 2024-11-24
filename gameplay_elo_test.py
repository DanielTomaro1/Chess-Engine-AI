import chess
import chess.engine
import statistics
from movegeneration import next_move
import time
import json
from datetime import datetime
import logging
from typing import List, Dict, Optional, Union, Tuple
import random
import math

class GameplayELOTester:
    def __init__(self, depth: int = 3, k_factor: int = 32):
        """Initialize the Gameplay-based ELO Tester."""
        # Create engine_analysis directory if it doesn't exist
        base_dir = "engine_analysis"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        # Set up logging to the engine_analysis directory
        log_file = os.path.join(base_dir, 'gameplay_elo_testing.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.base_dir = base_dir  # Store base directory
        
        self.depth = depth
        self.k_factor = k_factor
        self.current_elo = 1500  # Starting ELO
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.game_history = []
        
        # Define opponent pools with known ELOs
        self.opponent_pools = {
            'beginner': (800, 1200),
            'intermediate': (1200, 1600),
            'advanced': (1600, 2000),
            'expert': (2000, 2400)
        }

    def calculate_expected_score(self, player_elo: float, opponent_elo: float) -> float:
        """Calculate expected score using ELO formula."""
        return 1 / (1 + math.pow(10, (opponent_elo - player_elo) / 400))

    def update_elo(self, expected_score: float, actual_score: float) -> float:
        """Update ELO rating based on game result."""
        new_elo = self.current_elo + self.k_factor * (actual_score - expected_score)
        return new_elo

    def get_random_opponent_elo(self, skill_level: str) -> float:
        """Get a random opponent ELO within the specified skill range."""
        min_elo, max_elo = self.opponent_pools[skill_level]
        return random.uniform(min_elo, max_elo)

    def simulate_opponent_move(self, board: chess.Board, opponent_elo: float) -> chess.Move:
        """
        Simulate opponent moves based on their ELO rating.
        Higher rated opponents make better moves more frequently.
        """
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            raise ValueError("No legal moves available")

        # Basic move evaluation based on opponent's ELO
        move_scores = []
        for move in legal_moves:
            board.push(move)
            
            # Factors to consider in move evaluation
            is_check = board.is_check()
            is_capture = board.is_capture(move)
            attacked_squares = len(board.attacks(move.to_square))
            position_score = self.evaluate_position(board)
            
            # Pop the move back
            board.pop()
            
            # Calculate move score based on these factors
            move_score = position_score
            if is_check:
                move_score += 0.5
            if is_capture:
                move_score += 0.3
            move_score += attacked_squares * 0.1
            
            move_scores.append((move, move_score))

        # Higher ELO players are more likely to choose better moves
        elo_factor = (opponent_elo - 800) / 1600  # Normalized ELO (800-2400 range)
        if random.random() < elo_factor:
            # Choose one of the top moves
            move_scores.sort(key=lambda x: x[1], reverse=True)
            top_moves = move_scores[:max(1, int(len(move_scores) * 0.3))]
            return random.choice(top_moves)[0]
        else:
            # Choose a random move
            return random.choice(legal_moves)

    def evaluate_position(self, board: chess.Board) -> float:
        """
        Basic position evaluation.
        Returns a score from white's perspective.
        """
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0  # King's value not counted in material
        }
        
        score = 0.0
        
        # Material counting
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                value = piece_values[piece.piece_type]
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value
                    
        # Mobility (number of legal moves)
        board.turn = chess.WHITE
        white_moves = len(list(board.legal_moves))
        board.turn = chess.BLACK
        black_moves = len(list(board.legal_moves))
        score += (white_moves - black_moves) * 0.1
        
        return score

    def play_single_game(self, opponent_elo: float) -> Tuple[float, str]:
        """
        Simulate a single game against an opponent with known ELO.
        Returns: (actual_score, game_pgn)
        """
        board = chess.Board()
        game_moves = []
        is_engine_white = random.choice([True, False])
        
        while not board.is_game_over():
            try:
                if board.turn == chess.WHITE:
                    if is_engine_white:
                        # Engine's move
                        move = next_move(self.depth, board)
                        if move is None:
                            raise ValueError("Engine returned None move")
                    else:
                        # Simulate opponent's move
                        move = self.simulate_opponent_move(board, opponent_elo)
                else:
                    if is_engine_white:
                        move = self.simulate_opponent_move(board, opponent_elo)
                    else:
                        move = next_move(self.depth, board)
                        if move is None:
                            raise ValueError("Engine returned None move")
                
                board.push(move)
                game_moves.append(str(move))
                
            except Exception as e:
                self.logger.error(f"Error during game: {str(e)}")
                return 0.0, " ".join(game_moves)  # Count as loss if error occurs

        # Calculate game result
        if board.is_checkmate():
            if (board.result() == "1-0" and is_engine_white) or (board.result() == "0-1" and not is_engine_white):
                return 1.0, " ".join(game_moves)
            else:
                return 0.0, " ".join(game_moves)
        else:  # Draw
            return 0.5, " ".join(game_moves)

    def run_tournament(self, num_games: int = 100, adaptive: bool = True) -> Dict:
        """
        Run a tournament against opponents of various skill levels.
        
        Args:
            num_games: Number of games to play
            adaptive: If True, adjusts opponent selection based on current ELO
            
        Returns:
            Dict containing tournament results and statistics
        """
        self.logger.info(f"Starting tournament with {num_games} games...")
        
        for game_num in range(num_games):
            # Select opponent skill level based on current ELO if adaptive
            if adaptive:
                if self.current_elo < 1200:
                    skill_level = 'beginner'
                elif self.current_elo < 1600:
                    skill_level = 'intermediate'
                elif self.current_elo < 2000:
                    skill_level = 'advanced'
                else:
                    skill_level = 'expert'
            else:
                skill_level = random.choice(list(self.opponent_pools.keys()))
            
            opponent_elo = self.get_random_opponent_elo(skill_level)
            expected_score = self.calculate_expected_score(self.current_elo, opponent_elo)
            
            # Play the game
            actual_score, game_pgn = self.play_single_game(opponent_elo)
            
            # Update statistics
            self.games_played += 1
            if actual_score == 1.0:
                self.wins += 1
            elif actual_score == 0.0:
                self.losses += 1
            else:
                self.draws += 1
                
            # Update ELO
            new_elo = self.update_elo(expected_score, actual_score)
            
            # Log game results
            self.game_history.append({
                'game_number': game_num + 1,
                'opponent_elo': opponent_elo,
                'opponent_skill': skill_level,
                'expected_score': expected_score,
                'actual_score': actual_score,
                'old_elo': self.current_elo,
                'new_elo': new_elo,
                'elo_change': new_elo - self.current_elo,
                'game_pgn': game_pgn
            })
            
            self.current_elo = new_elo
            
            # Log progress
            if (game_num + 1) % 10 == 0:
                self.logger.info(f"Completed {game_num + 1} games. Current ELO: {self.current_elo:.1f}")

    def save_results(self, filename: Optional[str] = None) -> None:
        """Save tournament results to both text and JSON formats."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gameplay_elo_results_{timestamp}"
        
        # Add base directory to filename
        filepath = os.path.join(self.base_dir, filename)
        
        # Calculate final statistics
        win_rate = (self.wins / self.games_played) * 100
        draw_rate = (self.draws / self.games_played) * 100
        loss_rate = (self.losses / self.games_played) * 100
        
        elo_changes = [game['elo_change'] for game in self.game_history]
        avg_elo_change = statistics.mean(elo_changes)
        elo_volatility = statistics.stdev(elo_changes) if len(elo_changes) > 1 else 0
        
        # Save detailed text report
        with open(f"{filepath}.txt", 'w') as f:
            # ... rest of text saving remains the same ...
        
        # Save JSON format for programmatic access
        json_results = {
            'config': {
                'depth': self.depth,
                'k_factor': self.k_factor,
                'games_played': self.games_played
            },
            'final_results': {
                'final_elo': self.current_elo,
                'wins': self.wins,
                'draws': self.draws,
                'losses': self.losses,
                'win_rate': win_rate,
                'avg_elo_change': avg_elo_change,
                'elo_volatility': elo_volatility
            },
            'game_history': self.game_history
        }
        
        with open(f"{filepath}.json", 'w') as f:
            json.dump(json_results, f, indent=2)
            
        self.logger.info(f"Results saved to {filepath}.txt and {filepath}.json")

def main():
    """Main entry point with command line argument support."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chess Engine Gameplay ELO Testing")
    parser.add_argument("--depth", type=int, default=3, help="Search depth for the engine")
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    parser.add_argument("--k-factor", type=int, default=32, help="K-factor for ELO calculations")
    parser.add_argument("--no-adaptive", action="store_true", help="Disable adaptive opponent selection")
    
    args = parser.parse_args()
    
    try:
        tester = GameplayELOTester(depth=args.depth, k_factor=args.k_factor)
        results = tester.run_tournament(num_games=args.games, adaptive=not args.no_adaptive)
        tester.save_results()
        return 0
    except Exception as e:
        logging.error(f"Error during ELO testing: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
