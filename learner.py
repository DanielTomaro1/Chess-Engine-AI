from game_learner import GameLearner

def main():
    """Learn from saved games."""
    learner = GameLearner()
    
    # Learn from Stockfish matches
    print("Learning from Stockfish matches...")
    learner.learn_from_directory("stockfish_matches")
    
    # Learn from human games
    print("Learning from saved games...")
    learner.learn_from_directory("saved_games")
    
    # Save learned positions
    learner.save_experience()
    
    # Show some statistics
    print("\nLearned Positions:")
    print(f"Total positions: {len(learner.positions)}")
    total_moves = sum(len(moves) for moves in learner.positions.values())
    print(f"Total moves: {total_moves}")

if __name__ == "__main__":
    main()