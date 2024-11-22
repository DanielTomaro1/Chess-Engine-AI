import chess
import chess.engine
import statistics
from movegeneration import next_move
import time
import os
import json
from datetime import datetime
import logging
from typing import List, Dict, Optional, Union
import concurrent.futures

class ELOTester:
    def __init__(self, depth: int = 3, iterations: int = 10, use_multiprocessing: bool = True):
        """
        Initialize the ELO Tester with configurable parameters.
        
        Args:
            depth (int): Search depth for the engine
            iterations (int): Number of times to test each position
            use_multiprocessing (bool): Whether to use parallel processing for testing
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('elo_testing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.test_positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",  # Common opening
            "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 6 5",  # Italian Game
            "r3k2r/ppp2ppp/2n1bn2/2b1p3/2B1P3/2N2N2/PPP2PPP/R1BQ1RK1 b kq - 0 8",  # Complex middlegame
            "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",  # Tactical position
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",  # Endgame position
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",  # Complex position
        ]
        
        self.reference_points = {
            800: 0.5,     # 0.5 seconds for 800 ELO
            1000: 1.0,    # 1 second for 1000 ELO
            1200: 1.5,    # 1.5 seconds for 1200 ELO
            1500: 2.0,    # 2 seconds for 1500 ELO
            1800: 2.5,    # 2.5 seconds for 1800 ELO
            2000: 3.0,    # 3 seconds for 2000 ELO
            2200: 3.5,    # 3.5 seconds for 2200 ELO
            2500: 4.0     # 4 seconds for 2500 ELO
        }
        
        self.depth = depth
        self.iterations = iterations
        self.use_multiprocessing = use_multiprocessing
        self.results: List[Dict] = []

    def validate_fen(self, fen: str) -> bool:
        """Validate if a FEN string is legal"""
        try:
            chess.Board(fen)
            return True
        except ValueError:
            return False

    def test_single_position(self, fen: str) -> Dict[str, Union[float, List[str]]]:
        """
        Test engine's performance on a single position with error handling.
        """
        if not self.validate_fen(fen):
            raise ValueError(f"Invalid FEN string: {fen}")
            
        board = chess.Board(fen)
        times = []
        moves = []
        
        for _ in range(self.iterations):
            try:
                start_time = time.perf_counter()
                move = next_move(self.depth, board)
                end_time = time.perf_counter()
                
                if move is None:
                    raise ValueError("Engine returned None move")
                    
                times.append(end_time - start_time)
                moves.append(str(move))
                
            except Exception as e:
                self.logger.error(f"Error testing position {fen}: {str(e)}")
                continue
        
        if not times:
            raise RuntimeError(f"All attempts failed for position: {fen}")
            
        return {
            'avg_time': statistics.mean(times),
            'moves': moves,
            'min_time': min(times),
            'max_time': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0
        }

    def estimate_elo_from_time(self, solving_time: float) -> float:
        """Estimate ELO based on solving time using enhanced interpolation."""
        times = sorted(self.reference_points.values())
        elos = [k for k, v in self.reference_points.items()]  # Fix: Get ELOs directly
        
        if solving_time <= times[0]:
            return elos[0]
        if solving_time >= times[-1]:
            return elos[-1]
            
        for i in range(len(times) - 1):
            if times[i] <= solving_time <= times[i + 1]:
                time_ratio = (solving_time - times[i]) / (times[i + 1] - times[i])
                return elos[i] + time_ratio * (elos[i + 1] - elos[i])
        
        return elos[-1]

    def save_results(self, filename: Optional[str] = None) -> None:
        """Save test results to both text and JSON formats."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"elo_test_results_{timestamp}"
            
        # Save detailed text report
        with open(f"{filename}.txt", 'w') as f:
            f.write("Chess Engine ELO Test Results\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Test Configuration:\n")
            f.write(f"- Search depth: {self.depth}\n")
            f.write(f"- Iterations per position: {self.iterations}\n")
            f.write(f"- Number of positions: {len(self.test_positions)}\n\n")
            
            for i, result in enumerate(self.results):
                f.write(f"Position {i+1}:\n")
                f.write(f"FEN: {self.test_positions[i]}\n")
                f.write(f"Average solving time: {result['avg_time']:.3f} seconds\n")
                f.write(f"Time range: {result['min_time']:.3f} - {result['max_time']:.3f} seconds\n")
                f.write(f"Standard deviation: {result['std_dev']:.3f} seconds\n")
                f.write(f"Estimated ELO: {result['elo']:.0f}\n")
                f.write(f"Moves considered: {', '.join(result['moves'])}\n")
                f.write("-" * 50 + "\n\n")
            
            f.write("\nFinal Results:\n")
            f.write(f"Average ELO: {self.final_elo:.0f}\n")
            f.write(f"ELO Range: {self.min_elo:.0f} - {self.max_elo:.0f}\n")
            f.write(f"Standard Deviation: {self.elo_std:.0f}\n")
            
        # Save JSON format for programmatic access
        json_results = {
            'config': {
                'depth': self.depth,
                'iterations': self.iterations,
                'positions_tested': len(self.test_positions)
            },
            'positions': [
                {
                    'fen': self.test_positions[i],
                    **result
                } for i, result in enumerate(self.results)
            ],
            'final_results': {
                'average_elo': self.final_elo,
                'min_elo': self.min_elo,
                'max_elo': self.max_elo,
                'elo_std': self.elo_std
            }
        }
        
        with open(f"{filename}.json", 'w') as f:
            json.dump(json_results, f, indent=2)

    def process_position(self, fen: str) -> Optional[Dict]:
        """Process a single position and return results. This is a separate method for multiprocessing."""
        try:
            result = self.test_single_position(fen)
            elo = self.estimate_elo_from_time(result['avg_time'])
            return {**result, 'elo': elo}
        except Exception as e:
            self.logger.error(f"Failed to test position {fen}: {str(e)}")
            return None

    def run_elo_test(self) -> float:
        """Run complete ELO testing with parallel processing support."""
        self.logger.info("Starting ELO testing...")
        
        # Use parallel processing if enabled
        if self.use_multiprocessing:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = [executor.submit(self.process_position, fen) for fen in self.test_positions]
                self.results = [f.result() for f in futures if f.result() is not None]
        else:
            self.results = []
            for i, fen in enumerate(self.test_positions, 1):
                self.logger.info(f"Testing position {i}/{len(self.test_positions)}")
                result = self.process_position(fen)
                if result:
                    self.results.append(result)
                    self.logger.info(f"Position {i} ELO: {result['elo']:.0f}")
        
        if not self.results:
            raise RuntimeError("No valid results obtained from testing")
        
        # Calculate final statistics
        elos = [r['elo'] for r in self.results]
        self.final_elo = statistics.mean(elos)
        self.min_elo = min(elos)
        self.max_elo = max(elos)
        self.elo_std = statistics.stdev(elos)
        
        self.logger.info("\nFinal Results:")
        self.logger.info(f"Average ELO: {self.final_elo:.0f}")
        self.logger.info(f"ELO Range: {self.min_elo:.0f} - {self.max_elo:.0f}")
        self.logger.info(f"Standard Deviation: {self.elo_std:.0f}")
        
        # Save results
        self.save_results()
        return self.final_elo

def main():
    """Main entry point with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chess Engine ELO Testing Tool")
    parser.add_argument("--depth", type=int, default=3, help="Search depth for the engine")
    parser.add_argument("--iterations", type=int, default=10, help="Number of iterations per position")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel processing")
    
    args = parser.parse_args()
    
    try:
        tester = ELOTester(
            depth=args.depth,
            iterations=args.iterations,
            use_multiprocessing=not args.no_parallel
        )
        estimated_elo = tester.run_elo_test()
        return 0
    except Exception as e:
        logging.error(f"Error during ELO testing: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
