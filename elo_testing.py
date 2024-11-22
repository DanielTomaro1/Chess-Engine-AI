import chess
import chess.engine
import statistics
from movegeneration import next_move
import time
import os

class ELOTester:
    def __init__(self):
        self.test_positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",  # Common opening
            "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 6 5",  # Italian Game
            "r3k2r/ppp2ppp/2n1bn2/2b1p3/2B1P3/2N2N2/PPP2PPP/R1BQ1RK1 b kq - 0 8",  # Complex middlegame
            "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",  # Tactical position
        ]
        
        # Reference points (position : known ELO solving time)
        self.reference_points = {
            1000: 1.0,    # 1 second for 1000 ELO
            1500: 2.0,    # 2 seconds for 1500 ELO
            2000: 3.0,    # 3 seconds for 2000 ELO
            2500: 4.0     # 4 seconds for 2500 ELO
        }
        
        self.depth = 3  # Same depth as used in the GUI
        self.results = []

    def test_single_position(self, fen):
        """Test engine's performance on a single position"""
        board = chess.Board(fen)
        times = []
        moves = []

        # Test position multiple times for consistency
        for _ in range(3):
            start_time = time.time()
            move = next_move(self.depth, board)
            end_time = time.time()
            
            times.append(end_time - start_time)
            moves.append(move)

        return {
            'avg_time': statistics.mean(times),
            'moves': moves,
            'min_time': min(times),
            'max_time': max(times)
        }

    def estimate_elo_from_time(self, solving_time):
        """Estimate ELO based on solving time using linear interpolation"""
        times = list(self.reference_points.values())
        elos = list(self.reference_points.keys())
        
        for i in range(len(times)):
            if solving_time <= times[i]:
                if i == 0:
                    return elos[0]
                # Linear interpolation
                time_diff = times[i] - times[i-1]
                elo_diff = elos[i] - elos[i-1]
                ratio = (solving_time - times[i-1]) / time_diff
                return elos[i-1] + ratio * elo_diff
        
        return elos[-1]

    def save_results(self, filename='elo_test_results.txt'):
        """Save test results to a file"""
        with open(filename, 'w') as f:
            f.write("Chess Engine ELO Test Results\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Number of positions tested: {len(self.test_positions)}\n")
            f.write(f"Depth used: {self.depth}\n\n")
            
            for i, result in enumerate(self.results):
                f.write(f"Position {i+1}:\n")
                f.write(f"FEN: {self.test_positions[i]}\n")
                f.write(f"Average solving time: {result['avg_time']:.3f} seconds\n")
                f.write(f"Time range: {result['min_time']:.3f} - {result['max_time']:.3f} seconds\n")
                f.write(f"Estimated ELO: {result['elo']:.0f}\n")
                f.write(f"Moves considered: {', '.join(map(str, result['moves']))}\n")
                f.write("-" * 50 + "\n\n")
            
            f.write("\nFinal Results:\n")
            f.write(f"Average ELO: {self.final_elo:.0f}\n")
            f.write(f"ELO Range: {self.min_elo:.0f} - {self.max_elo:.0f}\n")
            f.write(f"Standard Deviation: {self.elo_std:.0f}\n")

    def run_elo_test(self):
        """Run complete ELO testing"""
        print("Starting ELO testing...")
        print("-" * 50)
        
        for i, position in enumerate(self.test_positions, 1):
            print(f"\nTesting position {i}/{len(self.test_positions)}")
            
            # Test the position
            result = self.test_single_position(position)
            
            # Estimate ELO for this position
            elo = self.estimate_elo_from_time(result['avg_time'])
            
            # Store results
            self.results.append({
                'avg_time': result['avg_time'],
                'min_time': result['min_time'],
                'max_time': result['max_time'],
                'moves': result['moves'],
                'elo': elo
            })
            
            print(f"Average solving time: {result['avg_time']:.3f} seconds")
            print(f"Estimated ELO: {elo:.0f}")
        
        # Calculate final statistics
        elos = [r['elo'] for r in self.results]
        self.final_elo = statistics.mean(elos)
        self.min_elo = min(elos)
        self.max_elo = max(elos)
        self.elo_std = statistics.stdev(elos)
        
        print("\nFinal Results:")
        print("=" * 50)
        print(f"Average ELO: {self.final_elo:.0f}")
        print(f"ELO Range: {self.min_elo:.0f} - {self.max_elo:.0f}")
        print(f"Standard Deviation: {self.elo_std:.0f}")
        
        # Save results to file
        self.save_results()
        print("\nDetailed results have been saved to 'elo_test_results.txt'")
        
        return self.final_elo

def main():
    print("Chess Engine ELO Testing")
    print("=" * 50)
    
    tester = ELOTester()
    estimated_elo = tester.run_elo_test()

if __name__ == "__main__":
    main()