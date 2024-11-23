from typing import Dict, Optional, Tuple, NamedTuple
import chess
import time
from dataclasses import dataclass
from enum import Enum

class NodeType(Enum):
    """Type of node in the transposition table"""
    EXACT = 1   # Exact score
    ALPHA = 2   # Upper bound
    BETA = 3    # Lower bound

@dataclass
class TableEntry:
    """Entry in the transposition table"""
    depth: int          # Depth of the search
    score: float        # Position score
    node_type: NodeType # Type of node (exact, upper bound, lower bound)
    best_move: Optional[chess.Move] # Best move found for this position
    age: int           # When this position was last accessed

class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        """
        Initialize transposition table.
        
        Args:
            size_mb: Size of the table in megabytes
        """
        # Calculate number of entries based on size
        entry_size = 32  # Approximate bytes per entry
        self.max_entries = (size_mb * 1024 * 1024) // entry_size
        self.table: Dict[int, TableEntry] = {}
        self.hits = 0
        self.misses = 0
        self.collisions = 0
        self.current_age = 0
    
    def store(self, board: chess.Board, depth: int, score: float, 
              node_type: NodeType, best_move: Optional[chess.Move] = None):
        """
        Store a position in the table.
        
        Args:
            board: Current board position
            depth: Search depth
            score: Position score
            node_type: Type of node
            best_move: Best move found for this position
        """
        # Get Zobrist hash of the position
        key = chess.polyglot.zobrist_hash(board)
        
        # Handle table size limit
        if len(self.table) >= self.max_entries:
            # Find and remove oldest entry
            oldest_key = min(self.table.keys(), 
                           key=lambda k: self.table[k].age)
            del self.table[oldest_key]
            self.collisions += 1
        
        # Store new entry
        self.table[key] = TableEntry(
            depth=depth,
            score=score,
            node_type=node_type,
            best_move=best_move,
            age=self.current_age
        )
        
    def lookup(self, board: chess.Board) -> Optional[TableEntry]:
        """
        Look up a position in the table.
        
        Args:
            board: Current board position
            
        Returns:
            TableEntry if found, None otherwise
        """
        key = chess.polyglot.zobrist_hash(board)
        entry = self.table.get(key)
        
        if entry is not None:
            self.hits += 1
            # Update age of accessed entry
            entry.age = self.current_age
            return entry
        
        self.misses += 1
        return None
    
    def new_search(self):
        """Call at the start of each new search."""
        self.current_age += 1
    
    def get_stats(self) -> Dict[str, int]:
        """Get table statistics."""
        return {
            "size": len(self.table),
            "max_size": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "collisions": self.collisions,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }
    
    def clear(self):
        """Clear the table."""
        self.table.clear()
        self.hits = 0
        self.misses = 0
        self.collisions = 0