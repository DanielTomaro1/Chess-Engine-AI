import chess
import chess.pgn
import os
import json
from collections import defaultdict
import datetime

class GameLearner:
    def __init__(self, experience_file="engine_analysis/learned_positions.json"):
        # Create base directory if it doesn't exist
        base_dir = "engine_analysis"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        self.positions = defaultdict(list)
        self.experience_file = experience_file
        self.load_experience()
        
        # Statistics tracking
        self.games_processed = 0
        self.positions_learned = 0
        self.total_moves = 0
        
    def load_experience(self):
        """Load previously learned positions."""
        try:
            if os.path.exists(self.experience_file):
                with open(self.experience_file, 'r') as f:
                    data = json.load(f)
                    self.positions = defaultdict(list, {k: v for k, v in data.items()})
                print(f"Loaded {len(self.positions)} learned positions")
        except Exception as e:
            print(f"Error loading experience file: {e}")
            self.positions = defaultdict(list)

    def save_experience(self):
        """Save learned positions to file."""
        try:
            with open(self.experience_file, 'w') as f:
                json.dump(dict(self.positions), f, indent=2)
            print(f"Saved {len(self.positions)} positions to {self.experience_file}")
        except Exception as e:
            print(f"Error saving experience file: {e}")

    def learn_from_directory(self, directory):
        """Learn from all PGN files in a directory."""
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist")
            return

        pgn_files = [f for f in os.listdir(directory) if f.endswith('.pgn')]
        total_files = len(pgn_files)
        print(f"Found {total_files} PGN files in {directory}")

        for i, filename in enumerate(pgn_files, 1):
            filepath = os.path.join(directory, filename)
            try:
                self.learn_from_pgn(filepath)
                print(f"Processed {i}/{total_files}: {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    def learn_from_pgn(self, pgn_file):
        """Learn from a single PGN file."""
        try:
            with open(pgn_file) as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    self.games_processed += 1
                    board = game.board()
                    
                    for move in game.mainline_moves():
                        # Convert position to FEN, excluding move numbers
                        fen_parts = board.fen().split(' ')
                        position_key = ' '.join(fen_parts[:4])
                        
                        # Store the move if it's not already stored for this position
                        move_uci = move.uci()
                        if move_uci not in self.positions[position_key]:
                            self.positions[position_key].append(move_uci)
                            self.positions_learned += 1
                            
                        board.push(move)
                        self.total_moves += 1
                        
        except Exception as e:
            print(f"Error processing PGN file {pgn_file}: {e}")

    def get_known_move(self, board):
        """Get a known move for a position if available."""
        fen_parts = board.fen().split(' ')
        position_key = ' '.join(fen_parts[:4])
        
        if position_key in self.positions:
            return self.positions[position_key]
        return None

    def get_statistics(self):
        """Get learning statistics."""
        return {
            'total_positions': len(self.positions),
            'total_moves': self.total_moves,
            'games_processed': self.games_processed,
            'positions_learned': self.positions_learned,
            'average_moves_per_position': 
                self.total_moves / len(self.positions) if self.positions else 0
        }

def integrate_with_batch_analysis(batch_match):
    """
    Integrate learning with the batch analysis system.
    This function should be called after each batch of games.
    """
    learner = GameLearner()
    
    # Learn from newly played games in the correct directory
    pgn_dir = "engine_analysis/pgn_games"
    print("\nLearning from new games...")
    learner.learn_from_directory(pgn_dir)
    
    # Rest remains the same...
    stats = learner.get_statistics()
    print("\nLearning Statistics:")
    print(f"Total positions learned: {stats['total_positions']}")
    print(f"Total moves stored: {stats['total_moves']}")
    print(f"Games processed: {stats['games_processed']}")
    print(f"New positions learned: {stats['positions_learned']}")
    print(f"Average moves per position: {stats['average_moves_per_position']:.2f}")
    
    learner.save_experience()

def main():
    """Main function for standalone learning."""
    learner = GameLearner()
    
    print("Chess Game Learning System")
    print("=" * 50)
    
    base_dir = "engine_analysis"
    
    # Learn from games in the correct directories
    print("\nLearning from PGN games...")
    learner.learn_from_directory(os.path.join(base_dir, "pgn_games"))
    
    # Save learned positions
    learner.save_experience()
    
    # Show statistics
    stats = learner.get_statistics()
    print("\nFinal Learning Statistics:")
    print(f"Total positions learned: {stats['total_positions']}")
    print(f"Total moves stored: {stats['total_moves']}")
    print(f"Games processed: {stats['games_processed']}")
    print(f"New positions learned: {stats['positions_learned']}")
    print(f"Average moves per position: {stats['average_moves_per_position']:.2f}")

if __name__ == "__main__":
    main()
