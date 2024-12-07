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
import multiprocessing
from functools import partial

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

def run_single_batch(config):
    start_game, batch_size, stockfish_elo, time_control = config
    
    # Initialize stockfish
    stockfish = chess.engine.SimpleEngine.popen_uci("/opt/homebrew/bin/stockfish")
    stockfish.configure({
        "UCI_LimitStrength": True,
        "UCI_Elo": stockfish_elo
    })
    
    batch_results = []
    try:
        for game_num in range(start_game, start_game + batch_size):
            try:
                my_engine_is_white = random.choice([True, False])
                board = chess.Board()
                game_stats = play_game(
                    game_num, 
                    stockfish_elo, 
                    time_control,
                    my_engine_is_white,
                    stockfish,
                    board
                )
                batch_results.append(game_stats)
                print(f"Completed game {game_num + 1}")
            except Exception as e:
                print(f"Error in game {game_num + 1}: {str(e)}")
    finally:
        stockfish.quit()
    
    return batch_results

def play_game(game_num, stockfish_elo, time_control, my_engine_is_white, stockfish, board):       
        print(f"\nStarting game {game_num + 1}...")
        print(f"Playing as {'White' if my_engine_is_white else 'Black'}")
        
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
        
        start_time = time.time()
        move_count = 0
        max_moves = 150
        move_timeout = 10
        
        # Track repeated positions
        position_count = defaultdict(int)
        repeated_position_limit = 3
        
        def material_difference_too_large(board):
            return abs(evaluate_board(board)) > 1500
            
        def is_likely_draw(board):
            if (len(list(board.pieces(chess.PAWN, chess.WHITE))) == 0 and 
                len(list(board.pieces(chess.PAWN, chess.BLACK))) == 0 and 
                len(list(board.pieces(chess.ROOK, chess.WHITE))) == 0 and 
                len(list(board.pieces(chess.ROOK, chess.BLACK))) == 0 and 
                len(list(board.pieces(chess.QUEEN, chess.WHITE))) == 0 and 
                len(list(board.pieces(chess.QUEEN, chess.BLACK))) == 0):
                return True
            return False

        while not board.is_game_over() and move_count < max_moves:
            move_count += 1
            move_start_time = time.time()
            
            # Check for repeated positions
            current_pos = board.fen().split(' ')[0]
            position_count[current_pos] += 1
            if position_count[current_pos] >= repeated_position_limit:
                print(f"Position repeated {repeated_position_limit} times - forcing draw")
                game_stats['termination'] = "repetition"
                game_stats['result'] = "1/2-1/2"
                game_stats['winner'] = "Draw"
                break
            
            # Check early stopping conditions
            if material_difference_too_large(board):
                game_stats['termination'] = "mercy_rule"
                game_stats['result'] = "1-0" if evaluate_board(board) > 0 else "0-1"
                game_stats['winner'] = "Draw"
                break
                
            if is_likely_draw(board):
                game_stats['termination'] = "likely_draw"
                game_stats['result'] = "1/2-1/2"
                game_stats['winner'] = "Draw"
                break

            try:
                is_engine_turn = (board.turn == chess.WHITE) == my_engine_is_white
                
                if is_engine_turn:
                    print(f"Engine thinking... (move {move_count})")
                    debug_info.clear()
                    move = next_move(2, board)  # Reduced depth for speed
                    is_book = debug_info.get("book_move", False)
                    if is_book:
                        game_stats['book_moves'] += 1
                    print(f"Engine chose move: {move}")
                else:
                    print(f"Stockfish thinking... (move {move_count})")
                    try:
                        result = stockfish.play(board, chess.engine.Limit(time=time_control))
                        move = result.move
                        print(f"Stockfish chose move: {move}")
                    except chess.engine.EngineTerminatedError:
                        print("Stockfish process terminated unexpectedly")
                        raise
                    except Exception as e:
                        print(f"Stockfish error: {str(e)}")
                        raise
                    is_book = False
                
                # Check for timeout
                if time.time() - move_start_time > move_timeout:
                    print(f"Move {move_count} timed out")
                    game_stats['termination'] = "timeout"
                    game_stats['result'] = "1/2-1/2"
                    game_stats['winner'] = "Draw"
                    break
                
                if move is None:
                    print(f"No move returned on move {move_count}")
                    game_stats['termination'] = "no_move"
                    game_stats['result'] = "1/2-1/2"
                    game_stats['winner'] = "Draw"
                    break
                    
                board.push(move)
                moves.append((move, is_book))
                game_stats['moves'].append({
                    'move': move.uci(),
                    'is_book': is_book,
                    'ply': len(board.move_stack),
                    'player': 'MyEngine' if is_engine_turn else 'Stockfish'
                })
                
                # Print move info with current evaluation
                eval_score = evaluate_board(board)
                print(f"Move {move_count}: {move.uci()} {'(book)' if is_book else ''} [Eval: {eval_score/100:.2f}]")
                
                # Small delay between moves
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error on move {move_count}: {str(e)}")
                print(f"Current position FEN: {board.fen()}")
                print(f"Legal moves: {list(board.legal_moves)}")
                raise
        
        game_stats['total_time'] = time.time() - start_time
        game_stats['num_moves'] = len(moves)
        
        # Handle game ending if not already set
        if not game_stats.get('result'):
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
        
        print(f"\nGame {game_num + 1} completed:")
        print(f"Result: {game_stats['result']}")
        print(f"Termination: {game_stats['termination']}")
        print(f"Moves played: {game_stats['num_moves']}")
        
        return game_stats    

class BatchEngineMatch:
    def __init__(self):
        # Create base directory structure
        self.base_dir = "engine_analysis"
        self.pgn_dir = os.path.join(self.base_dir, "pgn_games")
        self.stats_dir = os.path.join(self.base_dir, "statistics")
        
        for directory in [self.base_dir, self.pgn_dir, self.stats_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
        self.results = defaultdict(list)
        self.game_data = []
        self.stockfish = None  # Initialize stockfish as None
    
    def close(self):
        """Clean up resources."""
        # Only try to quit if stockfish exists and is running
        try:
            if hasattr(self, 'stockfish') and self.stockfish is not None:
                self.stockfish.quit()
        except Exception as e:
            print(f"Error closing stockfish: {e}")

        
    def run_game_batch(self, start_game, batch_size, stockfish_elo, time_control):
        """Run a batch of games."""
        stockfish = chess.engine.SimpleEngine.popen_uci("/opt/homebrew/bin/stockfish")
        stockfish.configure({
            "UCI_LimitStrength": True,
            "UCI_Elo": stockfish_elo
        })
        
        batch_results = []
        for game_num in range(start_game, start_game + batch_size):
            try:
                my_engine_is_white = random.choice([True, False])
                game_stats = self.play_single_game(
                    game_num, stockfish_elo, time_control, 
                    my_engine_is_white, stockfish
                )
                batch_results.append(game_stats)
                print(f"Completed game {game_num + 1}")
            except Exception as e:
                print(f"Error in game {game_num + 1}: {str(e)}")
        
        stockfish.quit()
        return batch_results

    def material_difference_too_large(self, board):
        """Check if material difference is too large."""
        return abs(evaluate_board(board)) > 1500  # 15 pawns worth
    
    def is_likely_draw(self, board):
        """Check for likely draw conditions."""
        # Only kings left
        if (len(list(board.pieces(chess.PAWN, chess.WHITE))) == 0 and 
            len(list(board.pieces(chess.PAWN, chess.BLACK))) == 0 and 
            len(list(board.pieces(chess.ROOK, chess.WHITE))) == 0 and 
            len(list(board.pieces(chess.ROOK, chess.BLACK))) == 0 and 
            len(list(board.pieces(chess.QUEEN, chess.WHITE))) == 0 and 
            len(list(board.pieces(chess.QUEEN, chess.BLACK))) == 0):
            return True
        return False
    def play_batch(self, num_games, stockfish_elo=1500, time_control=0.1, num_cores=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.stockfish_elo = stockfish_elo
        
        if num_cores is None:
            num_cores = multiprocessing.cpu_count() - 1
        num_cores = min(num_cores, num_games)
        
        print(f"\nStarting batch of {num_games} games using {num_cores} cores")
        
        # Create batch configurations
        batch_configs = []
        games_per_core = num_games // num_cores
        remaining_games = num_games % num_cores
        start_game = 0
        
        for i in range(num_cores):
            batch_size = games_per_core + (1 if i < remaining_games else 0)
            if batch_size > 0:
                batch_configs.append((start_game, batch_size, stockfish_elo, time_control))
                start_game += batch_size
        
        # Run games in parallel
        with multiprocessing.Pool(num_cores) as pool:
            all_results = pool.map(run_single_batch, batch_configs)
        
        # Combine results
        self.game_data = [game for batch in all_results for game in batch if game is not None]
        
        if self.game_data:
            # Save PGN files for each game
            for i, game_stats in enumerate(self.game_data):
                self.save_pgn(game_stats, timestamp, i)
                
            # Save statistics and learn from games
            self.save_statistics(timestamp, stockfish_elo)
            print("\nLearning from played games...")
            integrate_with_batch_analysis(self)
            
            return self.generate_summary()
        else:
            print("No games completed successfully")
            return None            
    def save_pgn(self, game_stats, timestamp, game_num):
        """Save individual game PGN."""
        # Just use the already initialized pgn_dir from __init__
        if not os.path.exists(self.pgn_dir):
            os.makedirs(self.pgn_dir)
            
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
        # Check if there's any data
        if not self.game_data:
            return None
        
        try:
            total_games = len(self.game_data)
            
            # Count results
            wins = sum(1 for game in self.game_data if 
                      (game['result'] == "1-0" and game['my_engine_played_white']) or 
                      (game['result'] == "0-1" and not game['my_engine_played_white']))
            losses = sum(1 for game in self.game_data if 
                        (game['result'] == "0-1" and game['my_engine_played_white']) or 
                        (game['result'] == "1-0" and not game['my_engine_played_white']))
            draws = sum(1 for game in self.game_data if game['result'] == "1/2-1/2")
            
            # Split games by color
            white_games = [game for game in self.game_data if game['my_engine_played_white']]
            black_games = [game for game in self.game_data if not game['my_engine_played_white']]
            
            # Calculate white statistics
            white_stats = {
                'games': len(white_games),
                'wins': sum(1 for game in white_games if game['result'] == "1-0"),
                'losses': sum(1 for game in white_games if game['result'] == "0-1"),
                'draws': sum(1 for game in white_games if game['result'] == "1/2-1/2")
            }
            if white_stats['games'] > 0:
                white_stats['win_rate'] = (white_stats['wins'] / white_stats['games']) * 100
                white_stats['loss_rate'] = (white_stats['losses'] / white_stats['games']) * 100
                white_stats['draw_rate'] = (white_stats['draws'] / white_stats['games']) * 100
            
            # Calculate black statistics
            black_stats = {
                'games': len(black_games),
                'wins': sum(1 for game in black_games if game['result'] == "0-1"),
                'losses': sum(1 for game in black_games if game['result'] == "1-0"),
                'draws': sum(1 for game in black_games if game['result'] == "1/2-1/2")
            }
            if black_stats['games'] > 0:
                black_stats['win_rate'] = (black_stats['wins'] / black_stats['games']) * 100
                black_stats['loss_rate'] = (black_stats['losses'] / black_stats['games']) * 100
                black_stats['draw_rate'] = (black_stats['draws'] / black_stats['games']) * 100
            
            # Calculate averages
            avg_moves = sum(game['num_moves'] for game in self.game_data) / total_games if total_games > 0 else 0
            avg_book_moves = sum(game['book_moves'] for game in self.game_data) / total_games if total_games > 0 else 0
            avg_time = sum(game['total_time'] for game in self.game_data) / total_games if total_games > 0 else 0
            
            # Count termination types
            termination_types = {}
            for game in self.game_data:
                term_type = game['termination']
                termination_types[term_type] = termination_types.get(term_type, 0) + 1
            
            # Create summary dictionary
            summary = {
                'total_games': total_games,
                'overall': {
                    'wins': wins,
                    'losses': losses,
                    'draws': draws,
                    'win_rate': (wins / total_games * 100) if total_games > 0 else 0,
                    'draw_rate': (draws / total_games * 100) if total_games > 0 else 0,
                    'loss_rate': (losses / total_games * 100) if total_games > 0 else 0
                },
                'as_white': white_stats,
                'as_black': black_stats,
                'avg_moves': avg_moves,
                'avg_book_moves': avg_book_moves,
                'avg_time_per_game': avg_time,
                'termination_types': termination_types
            }
            
            return summary
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return None

def main():
    print("Batch Chess Engine Analysis")
    print("=" * 50)

    # Get parameters from user
    while True:
        try:
            num_games = int(input("Enter number of games to play: "))
            elo = int(input("Enter Stockfish ELO (1000-3000): "))
            if 1000 <= elo <= 3000:
                break
            print("Please enter an ELO between 1000 and 3000")
        except ValueError:
            print("Please enter valid numbers")

    # Get number of cores for parallel processing
    num_cores = multiprocessing.cpu_count() - 1
    num_cores = min(num_cores, num_games)  # Don't use more cores than games
    print(f"\nUsing {num_cores} cores for parallel processing")

    # Create and run batch analysis
    batch = BatchEngineMatch()
    try:
        summary = batch.play_batch(num_games, stockfish_elo=elo, num_cores=num_cores)
        if summary:  # Check if summary exists
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
        else:
            print("\nNo valid summary generated")

    except KeyboardInterrupt:
        print("\nBatch analysis interrupted!")
        print("Saving partial results...")
        try:
            summary = batch.generate_summary()
            if summary:
                # Print available statistics...
                print("\nPartial Results:")
                print(f"Games completed: {summary['total_games']}")
        except Exception as e:
            print(f"Error generating partial summary: {e}")

    except Exception as e:
        print(f"\nError during batch analysis: {str(e)}")
        
    finally:
        batch.close()
        print("\nAnalysis session ended.")

if __name__ == "__main__":
    # Import at top of file
    import multiprocessing
    multiprocessing.freeze_support()  # For Windows compatibility
    main()
