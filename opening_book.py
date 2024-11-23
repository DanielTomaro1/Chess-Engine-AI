import chess
import chess.polyglot
import random
from typing import Optional, List, Tuple
import os
import logging

class OpeningBook:
    def __init__(self, book_path: str = "books/performance.bin"):
        """
        Initialize the opening book handler with a local book file.
        
        Args:
            book_path: Path to the local polyglot opening book file
        """
        self.book_path = book_path
        self.enabled = False
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Try to load the book
        try:
            if os.path.exists(book_path):
                self._reader = chess.polyglot.open_reader(book_path)
                self.enabled = True
                self.logger.info(f"Successfully loaded opening book: {book_path}")
            else:
                self.logger.warning(f"Opening book file not found at: {book_path}")
                print(f"Please make sure you have placed an opening book file at: {book_path}")
        except Exception as e:
            self.logger.error(f"Error loading opening book: {str(e)}")
            self.enabled = False

    def get_book_move(self, board: chess.Board, 
                      weighted: bool = True, 
                      min_weight: int = 10) -> Optional[chess.Move]:
        """
        Get a move from the opening book for the current position.
        
        Args:
            board: Current chess board position
            weighted: Whether to use weights when selecting moves
            min_weight: Minimum weight for a move to be considered
            
        Returns:
            chess.Move if a book move is found, None otherwise
        """
        if not self.enabled:
            return None
            
        try:
            entries = list(self._reader.find_all(board))
            
            # Filter entries by minimum weight
            valid_entries = [entry for entry in entries if entry.weight >= min_weight]
            
            if not valid_entries:
                return None
                
            if weighted:
                # Select move based on weights
                total_weight = sum(entry.weight for entry in valid_entries)
                choice = random.randint(0, total_weight - 1)
                
                current_weight = 0
                for entry in valid_entries:
                    current_weight += entry.weight
                    if current_weight > choice:
                        return entry.move
            else:
                # Select random move from valid entries
                entry = random.choice(valid_entries)
                return entry.move
                
        except Exception as e:
            self.logger.error(f"Error getting book move: {str(e)}")
            return None
        
        return None

    def get_book_moves_with_weights(self, board: chess.Board) -> List[Tuple[chess.Move, int]]:
        """
        Get all available book moves with their weights for the current position.
        
        Args:
            board: Current chess board position
            
        Returns:
            List of tuples containing (move, weight)
        """
        if not self.enabled:
            return []
            
        try:
            entries = list(self._reader.find_all(board))
            return [(entry.move, entry.weight) for entry in entries]
        except Exception as e:
            self.logger.error(f"Error getting book moves: {str(e)}")
            return []

    def is_in_book(self, board: chess.Board) -> bool:
        """
        Check if the current position is in the opening book.
        
        Args:
            board: Current chess board position
            
        Returns:
            Boolean indicating whether position is in book
        """
        if not self.enabled:
            return False
            
        try:
            entries = list(self._reader.find_all(board))
            return len(entries) > 0
        except Exception as e:
            self.logger.error(f"Error checking book position: {str(e)}")
            return False

    def close(self):
        """Close the opening book reader"""
        if self.enabled:
            try:
                self._reader.close()
            except Exception as e:
                self.logger.error(f"Error closing opening book: {str(e)}")