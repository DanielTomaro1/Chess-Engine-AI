import chess
import chess.engine
import chess.pgn
import time
import os
from datetime import datetime
import json
from collections import defaultdict
import pandas as pd
import numpy as np
from tqdm import tqdm
import random
from movegeneration import next_move, debug_info
from evaluate import evaluate_board
from game_learner import GameLearner

def integrate_with_batch_analysis(batch_match):
    """Integrate learning with the batch analysis system."""
    learner = GameLearner(experience_file="engine_analysis/learned_positions.json")
    
    print("\nLearning from played games...")
    learner.learn_from_directory("engine_analysis/pgn_games")
    
    # Get and display statistics
    stats = learner.get_statistics()
    
    print("\nLearning Statistics:")
    print(f"Total positions learned: {stats['total_positions']}")
    print(f"Total moves stored: {stats['total_moves']}")
    print(f"Average moves per position: {stats['average_moves_per_position']:.2f}")
    
    # Save the updated experience
    learner.save_experience()

class BatchEngineMatch:
    def __init__(self, stockfish_path="/opt/homebrew/bin/stockfish"):
        self.stockfish = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.results = defaultdict(list)
        self.game_data = []
        
        # Ensure directories exist
        self.base_dir = "engine_analysis"
        self.pgn_dir = os.path.join(self.base_dir, "pgn_games")
        self.stats_dir = os.path.join(self.base_dir, "statistics")
        
        for directory in [self.base_dir, self.pgn_dir, self.stats_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def play_batch(self, num_games, stockfish_elo=1500, time_control=1.0):
        """Play multiple games and collect statistics."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
        # Store stockfish_elo as instance variable
        self.stockfish_elo = stockfish_elo
    
        # Configure Stockfish
        self.stockfish.configure({
            "UCI_LimitStrength": True,
            "UCI_Elo": stockfish_elo
        })
    
        # Reset statistics
        self.results.clear()
        self.game_data.clear()
    
        print(f"Starting batch of {num_games} games against Stockfish (ELO: {stockfish_elo})")
    
        # Initialize learning system
        learner = GameLearner()
    
        # Play games
        for game_num in tqdm(range(num_games), desc="Playing games"):
            try:
                # Randomly decide who plays white
                my_engine_is_white = random.choice([True, False])
            
                # Play the game
                print(f"\nStarting game {game_num + 1}...")
                print(f"Playing as {'White' if my_engine_is_white else 'Black'}")
            
                game_stats = self.play_single_game(game_num, stockfish_elo, time_control, my_engine_is_white)
                self.game_data.append(game_stats)
            
                # Save PGN after each game
                self.save_pgn(game_stats, timestamp, game_num)
            
                # Update progress
                games_completed = game_num + 1
                print(f"\nCompleted {games_completed}/{num_games} games")
                print(f"Current stats: Wins: {self.results['results'].count('1-0')}, "
                    f"Draws: {self.results['results'].count('1/2-1/2')}, "
                    f"Losses: {self.results['results'].count('0-1')}")
            
            except Exception as e:
                print(f"Error in game {game_num + 1}: {str(e)}")
                continue
    
        # Save final statistics
        self.save_statistics(timestamp, stockfish_elo)
    
        # Learn from the games just played
        print("\nLearning from played games...")
        integrate_with_batch_analysis(self)
    
        # Generate and print final summary
        summary = self.generate_summary()
    
        print("\nBatch Analysis Complete!")
        print("=" * 50)
        print("Final Statistics:")
        print(f"Total Games: {summary['total_games']}")
        print("\nOverall Performance:")
        print(f"Win Rate: {summary['overall']['win_rate']:.1f}%")
        print(f"Draw Rate: {summary['overall']['draw_rate']:.1f}%")
        print(f"Loss Rate: {summary['overall']['loss_rate']:.1f}%")
    
        print("\nPerformance as White:")
        print(f"Games: {summary['as_white']['games']}")
        print(f"Win Rate: {summary['as_white'].get('win_rate', 0):.1f}%")
    
        print("\nPerformance as Black:")
        print(f"Games: {summary['as_black']['games']}")
        print(f"Win Rate: {summary['as_black'].get('win_rate', 0):.1f}%")
    
        print(f"\nAverage Moves per Game: {summary['avg_moves']:.1f}")
        print(f"Average Book Moves per Game: {summary['avg_book_moves']:.1f}")
        print(f"Average Time per Game: {summary['avg_time_per_game']:.1f} seconds")
    
        print("\nTermination Types:")
        for term_type, count in summary['termination_types'].items():
            print(f"  {term_type}: {count}")
    
        return summary

    def play_single_game(self, game_num, stockfish_elo, time_control, my_engine_is_white):
        print(f"\nStarting game {game_num + 1}...")  # Debug print
        board = chess.Board()
        moves = []
        game_stats = {
            'game_number': game_num + 1,
            'my_engine_played_white': my_engine_is_white,
            'moves': [],
            'num_moves': 0,
            'book_moves': 0,
            'result': None,
            'winner': None,
            'termination': None,
            'total_time': 0,
        }
    
        print(f"Playing as {'White' if my_engine_is_white else 'Black'}")  # Debug print
        start_time = time.time()
    
        move_count = 0
        while not board.is_game_over():
            move_count += 1
            print(f"Move {move_count}")  # Debug print
            is_engine_turn = (board.turn == chess.WHITE) == my_engine_is_white
        
            if is_engine_turn:
                print("Our engine thinking...")  # Debug print
                move = next_move(3, board)
                is_book = debug_info.get("book_move", False)
                if is_book:
                    game_stats['book_moves'] += 1
            else:
                print("Stockfish thinking...")  # Debug print
                result = self.stockfish.play(board, chess.engine.Limit(time=time_control))
                move = result.move
                is_book = False
            
            board.push(move)
            moves.append((move, is_book))
            game_stats['moves'].append({
                'move': move.uci(),
                'is_book': is_book,
                'ply': len(board.move_stack),
                'player': 'MyEngine' if is_engine_turn else 'Stockfish'
            })
        
        game_stats['total_time'] = time.time() - start_time
        game_stats['num_moves'] = len(moves)
        
        # Record game result, adjusting for who played which color
        if board.is_checkmate():
            white_won = board.turn == chess.BLACK
            if white_won == my_engine_is_white:
                winner = "MyEngine"
                result = "1-0"
            else:
                winner = "Stockfish"
                result = "0-1"
            game_stats['termination'] = "checkmate"
        elif board.is_stalemate():
            winner = "Draw"
            result = "1/2-1/2"
            game_stats['termination'] = "stalemate"
        elif board.is_insufficient_material():
            winner = "Draw"
            result = "1/2-1/2"
            game_stats['termination'] = "insufficient_material"
        else:
            winner = "Draw"
            result = "1/2-1/2"
            game_stats['termination'] = "other"
        
        game_stats['winner'] = winner
        game_stats['result'] = result
        
        # Update aggregated results
        self.results['results'].append(result)
        self.results['colors'].append('White' if my_engine_is_white else 'Black')
        self.results['terminations'].append(game_stats['termination'])
        self.results['num_moves'].append(game_stats['num_moves'])
        self.results['book_moves'].append(game_stats['book_moves'])
        self.results['total_time'].append(game_stats['total_time'])
        
        return game_stats

    def save_pgn(self, game_stats, timestamp, game_num):
        """Save individual game PGN."""
        # Ensure pgn_games directory exists within engine_analysis
        pgn_dir = os.path.join(self.base_dir, "pgn_games")
        if not os.path.exists(pgn_dir):
            os.makedirs(pgn_dir)
        game = chess.pgn.Game()
        
        # Set headers
        game.headers["Event"] = f"Batch Analysis Game {game_num + 1}"
        game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        
        # Set player names based on who played which color
        if game_stats['my_engine_played_white']:
            game.headers["White"] = "MyEngine"
            game.headers["Black"] = "Stockfish"
        else:
            game.headers["White"] = "Stockfish"
            game.headers["Black"] = "MyEngine"
            
        game.headers["Result"] = game_stats['result']
        game.headers["BlackElo"] = str(self.stockfish_elo) if game_stats['my_engine_played_white'] else "?"
        game.headers["WhiteElo"] = "?" if game_stats['my_engine_played_white'] else str(self.stockfish_elo)
        game.headers["Termination"] = game_stats['termination']
        
        # Add moves
        node = game
        for move_data in game_stats['moves']:
            move = chess.Move.from_uci(move_data['move'])
            node = node.add_variation(move)
            if move_data['is_book']:
                node.comment = "Book move"
        
        # Save to file
        filename = f"game_{timestamp}_{game_num + 1}.pgn"
        filepath = os.path.join(self.pgn_dir, filename)
        
        with open(filepath, "w") as f:
            print(game, file=f, end="\n\n")

    def save_statistics(self, timestamp, stockfish_elo):
        """Save comprehensive statistics to JSON and CSV."""
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        stats = {
            'timestamp': timestamp,
            'stockfish_elo': stockfish_elo,
            'num_games': len(self.game_data),
            'summary': convert_numpy(self.generate_summary()),
            'game_data': convert_numpy(self.game_data)
        }
        
        try:
            # Save detailed JSON
            json_path = os.path.join(self.stats_dir, f"stats_{timestamp}.json")
            with open(json_path, "w") as f:
                json.dump(stats, f, indent=2)
            print(f"\nStatistics saved to: {json_path}")
            
            # Save CSV summary
            df = pd.DataFrame(self.game_data)
            csv_path = os.path.join(self.stats_dir, f"summary_{timestamp}.csv")
            df.to_csv(csv_path, index=False)
            print(f"Summary saved to: {csv_path}")
            
        except Exception as e:
            print(f"Error saving statistics: {str(e)}")

    def generate_summary(self):
        """Generate summary statistics."""
        total_games = len(self.results['results'])
        if total_games == 0:
            return "No games played"
        
        wins = self.results['results'].count("1-0")
        losses = self.results['results'].count("0-1")
        draws = self.results['results'].count("1/2-1/2")
        
        # Split statistics by color
        white_games = [i for i, color in enumerate(self.results['colors']) if color == 'White']
        black_games = [i for i, color in enumerate(self.results['colors']) if color == 'Black']
        
        white_results = [self.results['results'][i] for i in white_games]
        black_results = [self.results['results'][i] for i in black_games]
        
        summary = {
            'total_games': total_games,
            'overall': {
                'wins': wins,
                'losses': losses,
                'draws': draws,
                'win_rate': wins / total_games * 100,
                'draw_rate': draws / total_games * 100,
                'loss_rate': losses / total_games * 100,
            },
            'as_white': {
                'games': len(white_games),
                'wins': white_results.count("1-0"),
                'losses': white_results.count("0-1"),
                'draws': white_results.count("1/2-1/2"),
            },
            'as_black': {
                'games': len(black_games),
                'wins': black_results.count("1-0"),
                'losses': black_results.count("0-1"),
                'draws': black_results.count("1/2-1/2"),
            },
            'avg_moves': sum(self.results['num_moves']) / total_games,
            'avg_book_moves': sum(self.results['book_moves']) / total_games,
            'avg_time_per_game': sum(self.results['total_time']) / total_games,
            'termination_types': dict(pd.Series(self.results['terminations']).value_counts()),
        }
        
        # Calculate win rates by color
        for color in ['as_white', 'as_black']:
            if summary[color]['games'] > 0:
                summary[color]['win_rate'] = summary[color]['wins'] / summary[color]['games'] * 100
                summary[color]['draw_rate'] = summary[color]['draws'] / summary[color]['games'] * 100
                summary[color]['loss_rate'] = summary[color]['losses'] / summary[color]['games'] * 100
        
        return summary

    def close(self):
        """Clean up resources."""
        if self.stockfish:
            self.stockfish.quit()

def main():
    print("Batch Chess Engine Analysis")
    print("=" * 50)
    
    # Get parameters from user
    num_games = int(input("Enter number of games to play: "))
    elo = int(input("Enter Stockfish ELO (1000-3000): "))
    
    # Create and run batch analysis
    batch = BatchEngineMatch()
    try:
        summary = batch.play_batch(num_games, stockfish_elo=elo)
        
        print("\nAnalysis Complete!")
        print("=" * 50)
        print("Overall Statistics:")
        print(f"Total Games: {summary['total_games']}")
        print(f"Overall Win Rate: {summary['overall']['win_rate']:.1f}%")
        print(f"Overall Draw Rate: {summary['overall']['draw_rate']:.1f}%")
        print(f"Overall Loss Rate: {summary['overall']['loss_rate']:.1f}%")
        
        print("\nPerformance as White:")
        print(f"Games: {summary['as_white']['games']}")
        print(f"Win Rate: {summary['as_white'].get('win_rate', 0):.1f}%")
        print(f"Draw Rate: {summary['as_white'].get('draw_rate', 0):.1f}%")
        print(f"Loss Rate: {summary['as_white'].get('loss_rate', 0):.1f}%")
        
        print("\nPerformance as Black:")
        print(f"Games: {summary['as_black']['games']}")
        print(f"Win Rate: {summary['as_black'].get('win_rate', 0):.1f}%")
        print(f"Draw Rate: {summary['as_black'].get('draw_rate', 0):.1f}%")
        print(f"Loss Rate: {summary['as_black'].get('loss_rate', 0):.1f}%")
        
        print(f"\nAverage Moves per Game: {summary['avg_moves']:.1f}")
        print(f"Average Book Moves per Game: {summary['avg_book_moves']:.1f}")
        print(f"Average Time per Game: {summary['avg_time_per_game']:.1f} seconds")
        
        print("\nTermination Types:")
        for term_type, count in summary['termination_types'].items():
            print(f"  {term_type}: {count}")
        
    finally:
        batch.close()

if __name__ == "__main__":
    main()
