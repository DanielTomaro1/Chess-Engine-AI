import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

class ChessStatsAnalyzer:
    def __init__(self, base_dir="engine_analysis"):
        self.base_dir = base_dir
        self.stats_dir = os.path.join(base_dir, "statistics")
        self.pgn_dir = os.path.join(base_dir, "pgn_games")
        
        # Ensure directories exist
        for directory in [self.base_dir, self.stats_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Initialize statistics containers
        self.game_stats = []
        self.learning_stats = {}
        self.elo_stats = {}
        
    def load_all_stats(self):
            """Load all available statistics."""
            self._load_game_stats()
            self._load_learning_stats()
            self._load_elo_stats()
        
    def _load_game_stats(self):
            """Load statistics from all JSON files in stats directory."""
            for file in os.listdir(self.stats_dir):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(self.stats_dir, file), 'r') as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                self.game_stats.append(data)
                    except Exception as e:
                        print(f"Error loading {file}: {e}")
    def _load_learning_stats(self):
        """Load learning statistics from learned_positions.json."""
        try:
            learning_file = os.path.join(self.base_dir, "learned_positions.json")
            if os.path.exists(learning_file):
                with open(learning_file, 'r') as f:
                    self.learning_stats = json.load(f)
        except Exception as e:
            print(f"Error loading learning stats: {e}")

    def _load_elo_stats(self):
            """Load ELO testing results."""
            elo_files = [f for f in os.listdir(self.base_dir) 
                        if f.startswith('gameplay_elo_results_') and f.endswith('.json')]
            for file in elo_files:
                try:
                    with open(os.path.join(self.base_dir, file), 'r') as f:
                        self.elo_stats[file] = json.load(f)
                except Exception as e:
                    print(f"Error loading ELO stats from {file}: {e}")

    def generate_comprehensive_report(self, output_file=None):
            """Generate a comprehensive statistical report."""
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = os.path.join(self.stats_dir, f"comprehensive_report_{timestamp}.txt")

            with open(output_file, 'w') as f:
                f.write("Chess Engine Comprehensive Analysis Report\n")
                f.write("=" * 50 + "\n\n")

                # Overall Statistics
                f.write("Overall Performance Statistics\n")
                f.write("-" * 30 + "\n")
                overall_stats = self._calculate_overall_stats()
                for key, value in overall_stats.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

                # Learning Progress
                f.write("Learning System Statistics\n")
                f.write("-" * 30 + "\n")
                if self.learning_stats:
                    f.write(f"Total Positions: {len(self.learning_stats)}\n")
                else:
                    f.write("No learning statistics available\n")
                f.write("\n")

                # ELO Progress
                f.write("ELO Rating Progress\n")
                f.write("-" * 30 + "\n")
                if self.elo_stats:
                    latest_elo = max(
                        test.get('final_results', {}).get('final_elo', 0) 
                        for test in self.elo_stats.values()
                    )
                    f.write(f"Latest ELO: {latest_elo}\n")
                else:
                    f.write("No ELO statistics available\n")

            return output_file

    def _calculate_overall_stats(self) -> Dict[str, Any]:
            """Calculate overall statistics from all games."""
            total_games = 0
            total_wins = 0
            total_draws = 0
            total_losses = 0
            total_moves = 0
            
            try:
                for stats in self.game_stats:
                    if isinstance(stats, str):
                        continue
                        
                    if 'summary' in stats:
                        summary = stats['summary']
                        if isinstance(summary, dict):
                            total_games += summary.get('total_games', 0)
                            overall = summary.get('overall', {})
                            total_wins += overall.get('wins', 0)
                            total_draws += overall.get('draws', 0)
                            total_losses += overall.get('losses', 0)
                            total_moves += summary.get('avg_moves', 0) * summary.get('total_games', 0)

                return {
                    'Total Games': total_games,
                    'Total Wins': total_wins,
                    'Total Draws': total_draws,
                    'Total Losses': total_losses,
                    'Win Rate': f"{(total_wins/total_games)*100:.2f}%" if total_games > 0 else "N/A",
                    'Average Moves per Game': f"{total_moves/total_games:.1f}" if total_games > 0 else "N/A"
                }
            except Exception as e:
                print(f"Error calculating overall stats: {e}")
                return {
                    'Total Games': 0,
                    'Total Wins': 0,
                    'Total Draws': 0,
                    'Total Losses': 0,
                    'Win Rate': "N/A",
                    'Average Moves per Game': "N/A"
                }            
    def _calculate_learning_stats(self) -> Dict[str, Any]:
        """Calculate learning system statistics."""
        return {
            'Total Positions Learned': len(self.learning_stats),
            'Average Moves per Position': sum(len(moves) for moves in self.learning_stats.values()) / len(self.learning_stats) if self.learning_stats else 0,
            'Book Moves Learned': sum(1 for moves in self.learning_stats.values() for move in moves if move.get('is_book', False))
        }

    def _calculate_elo_stats(self) -> Dict[str, Any]:
        """Calculate ELO rating statistics."""
        if not self.elo_stats:
            return {'No ELO data available': 'N/A'}

        elo_ratings = []
        for test in self.elo_stats.values():
            if 'final_results' in test:
                elo_ratings.append(test['final_results'].get('final_elo', 0))

        return {
            'Number of ELO Tests': len(self.elo_stats),
            'Latest ELO Rating': max(elo_ratings) if elo_ratings else 'N/A',
            'Average ELO Rating': sum(elo_ratings)/len(elo_ratings) if elo_ratings else 'N/A',
            'ELO Rating Range': f"{min(elo_ratings)}-{max(elo_ratings)}" if elo_ratings else 'N/A'
        }

    def _calculate_color_stats(self) -> Dict[str, Dict[str, Any]]:
        """Calculate performance statistics by color."""
        white_stats = defaultdict(int)
        black_stats = defaultdict(int)

        for stats in self.game_stats:
            if 'summary' in stats:
                summary = stats['summary']
                if 'as_white' in summary:
                    white = summary['as_white']
                    white_stats['games'] += white.get('games', 0)
                    white_stats['wins'] += white.get('wins', 0)
                    white_stats['draws'] += white.get('draws', 0)
                    white_stats['losses'] += white.get('losses', 0)

                if 'as_black' in summary:
                    black = summary['as_black']
                    black_stats['games'] += black.get('games', 0)
                    black_stats['wins'] += black.get('wins', 0)
                    black_stats['draws'] += black.get('draws', 0)
                    black_stats['losses'] += black.get('losses', 0)

        return {
            'White': {
                'Games': white_stats['games'],
                'Win Rate': f"{(white_stats['wins']/white_stats['games'])*100:.2f}%" if white_stats['games'] > 0 else "N/A",
                'Draw Rate': f"{(white_stats['draws']/white_stats['games'])*100:.2f}%" if white_stats['games'] > 0 else "N/A"
            },
            'Black': {
                'Games': black_stats['games'],
                'Win Rate': f"{(black_stats['wins']/black_stats['games'])*100:.2f}%" if black_stats['games'] > 0 else "N/A",
                'Draw Rate': f"{(black_stats['draws']/black_stats['games'])*100:.2f}%" if black_stats['games'] > 0 else "N/A"
            }
        }

    def plot_elo_progress(self, output_file=None):
        """Generate a plot showing ELO rating progress over time."""
        if not self.elo_stats:
            print("No ELO data available for plotting")
            return

        plt.figure(figsize=(12, 6))
        for test_file, test_data in self.elo_stats.items():
            if 'game_history' in test_data:
                games = test_data['game_history']
                elo_ratings = [game['new_elo'] for game in games]
                plt.plot(range(len(elo_ratings)), elo_ratings, label=test_file.split('.')[0])

        plt.title('ELO Rating Progress')
        plt.xlabel('Games Played')
        plt.ylabel('ELO Rating')
        plt.legend()
        plt.grid(True)

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.stats_dir, f"elo_progress_{timestamp}.png")

        plt.savefig(output_file)
        plt.close()
        return output_file

def main():
    """Main function to generate comprehensive statistics."""
    analyzer = ChessStatsAnalyzer()
    
    print("Chess Engine Statistics Analysis")
    print("=" * 50)
    
    try:
        analyzer.load_all_stats()
        
        # Generate comprehensive report
        report_file = analyzer.generate_comprehensive_report()
        if report_file:
            print(f"Comprehensive report generated: {report_file}")
            
            # Display some key statistics
            print("\nKey Statistics:")
            stats = analyzer._calculate_overall_stats()
            for key, value in stats.items():
                print(f"{key}: {value}")
        else:
            print("No statistics available to analyze")
            
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    print("\nAnalysis complete")

if __name__ == "__main__":
    main()
