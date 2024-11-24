import chess
import chess.pgn
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import io

class PGNHandler:
    def __init__(self, directory="pgn_games"):
        """
        Initialize PGN handler with a directory for saved games.
        
        Args:
            directory: Directory for saving and loading PGN files
        """
        self.directory = directory
        if not os.path.exists(directory):
            os.makedirs(directory)
            
    def save_game(self, board: chess.Board, headers: Dict[str, str] = None) -> str:
        """
        Save a chess game in PGN format.
        
        Args:
            board: The chess board containing the game moves
            headers: Optional dictionary of PGN headers
            
        Returns:
            str: Path to the saved PGN file
        """
        game = chess.pgn.Game()
        
        # Set default headers
        default_headers = {
            "Event": "Chess Game",
            "Site": "Local Computer",
            "Date": datetime.now().strftime("%Y.%m.%d"),
            "Round": "1",
            "White": "Player",
            "Black": "Engine",
            "Result": self._get_result(board)
        }
        
        # Update with custom headers if provided
        if headers:
            default_headers.update(headers)
        
        # Set all headers
        for key, value in default_headers.items():
            game.headers[key] = value
        
        # Add moves
        node = game
        for move in board.move_stack:
            node = node.add_variation(move)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_{timestamp}.pgn"
        filepath = os.path.join(self.directory, filename)
        
        # Save to file
        with open(filepath, "w") as f:
            print(game, file=f, end="\n\n")
        
        return filepath
    
    def load_game(self, filepath: str) -> Optional[chess.pgn.Game]:
        """
        Load a game from a PGN file.
        
        Args:
            filepath: Path to the PGN file
            
        Returns:
            Optional[chess.pgn.Game]: Loaded game or None if loading fails
        """
        try:
            with open(filepath) as f:
                return chess.pgn.read_game(f)
        except Exception as e:
            print(f"Error loading game: {e}")
            return None
    
    def load_game_from_string(self, pgn_string: str) -> Optional[chess.pgn.Game]:
        """
        Load a game from a PGN string.
        
        Args:
            pgn_string: String containing PGN data
            
        Returns:
            Optional[chess.pgn.Game]: Loaded game or None if loading fails
        """
        try:
            return chess.pgn.read_game(io.StringIO(pgn_string))
        except Exception as e:
            print(f"Error loading game from string: {e}")
            return None
    
    def get_all_games(self) -> List[str]:
        """
        Get a list of all saved PGN files.
        
        Returns:
            List[str]: List of PGN file paths
        """
        return [os.path.join(self.directory, f) 
                for f in os.listdir(self.directory) 
                if f.endswith('.pgn')]
    
    def _get_result(self, board: chess.Board) -> str:
        """Get the game result in PGN format."""
        if not board.is_game_over():
            return "*"
        if board.is_checkmate():
            return "1-0" if board.turn == chess.BLACK else "0-1"
        return "1/2-1/2"  # Draw

    def export_to_string(self, board: chess.Board, headers: Dict[str, str] = None) -> str:
        """
        Export a game to PGN string format.
        
        Args:
            board: The chess board containing the game moves
            headers: Optional dictionary of PGN headers
            
        Returns:
            str: PGN string representation of the game
        """
        game = chess.pgn.Game()
        
        # Set headers
        default_headers = {
            "Event": "Chess Game",
            "Site": "Local Computer",
            "Date": datetime.now().strftime("%Y.%m.%d"),
        }
        
        if headers:
            default_headers.update(headers)
            
        for key, value in default_headers.items():
            game.headers[key] = value
        
        # Add moves
        node = game
        for move in board.move_stack:
            node = node.add_variation(move)
        
        # Convert to string
        output = io.StringIO()
        print(game, file=output, end="\n\n")
        return output.getvalue()
