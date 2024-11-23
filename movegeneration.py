from typing import Dict, List, Any
import chess
import sys
import time
from evaluate import evaluate_board, move_value, check_end_game
from opening_book import OpeningBook

debug_info: Dict[str, Any] = {}

MATE_SCORE = 1000000000
MATE_THRESHOLD = 999000000

# Initialize opening book
# Use absolute path to the book file
BOOK_PATH = "/Users/danieltomaro/Documents/Projects/Chess-Engine-AI/books/Perfect2021.bin"

# Initialize opening book with absolute path
book = OpeningBook(BOOK_PATH)

def quiescence_search(board: chess.Board, alpha: float, beta: float, depth: int = 4) -> tuple[float, int]:
    """
    Quiescence search to evaluate only "quiet" positions.
    
    Args:
        board: Current chess board position
        alpha: Alpha value for alpha-beta pruning
        beta: Beta value for alpha-beta pruning
        depth: Maximum depth for quiescence search
        
    Returns:
        Tuple of (evaluation, nodes searched)
    """
    nodes = 1
    stand_pat = evaluate_board(board)
    
    # Return immediately if checkmate is found
    if board.is_checkmate():
        return -MATE_SCORE if board.turn else MATE_SCORE, nodes
        
    # Stand pat (static evaluation) if we've gone too deep
    if depth == 0:
        return stand_pat, nodes
        
    # Delta pruning
    if stand_pat >= beta:
        return beta, nodes
    if alpha < stand_pat:
        alpha = stand_pat

    # Look at capturing moves only
    for move in board.legal_moves:
        if not board.is_capture(move):
            continue
            
        board.push(move)
        score, child_nodes = quiescence_search(board, -beta, -alpha, depth - 1)
        score = -score
        board.pop()
        
        nodes += child_nodes
        
        if score >= beta:
            return beta, nodes
        if score > alpha:
            alpha = score
            
    return alpha, nodes


def next_move(depth: int, board: chess.Board, debug=True) -> chess.Move:
    """
    What is the next best move?
    First checks opening book, then falls back to engine calculation.
    """
    debug_info.clear()
    debug_info["nodes"] = 0
    t0 = time.time()

    print("\n--- Checking for book move ---")
    # Try to get a book move first
    book_move = book.get_book_move(board)
    if book_move is not None:
        debug_info["time"] = time.time() - t0
        debug_info["book_move"] = True
        print(f"✓ Using book move: {book_move}")
        if debug:
            print(f"info {debug_info}")
        return book_move
    else:
        print("✗ No book move found, calculating...")

    # Fall back to engine calculation if no book move is found
    move = minimax_root(depth, board)
    
    debug_info["time"] = time.time() - t0
    debug_info["book_move"] = False
    if debug:
        print(f"info {debug_info}")
    return move
##############################################################################################
def get_ordered_moves(board: chess.Board) -> List[chess.Move]:
    """
    Get legal moves.
    Attempt to sort moves by best to worst.
    Use piece values (and positional gains/losses) to weight captures.
    """
    end_game = check_end_game(board)

    def orderer(move):
        return move_value(board, move, end_game)

    in_order = sorted(
        board.legal_moves, key=orderer, reverse=(board.turn == chess.WHITE)
    )
    return list(in_order)
##############################################################################################
def minimax_root(depth: int, board: chess.Board) -> chess.Move:
    """
    What is the highest value move per our evaluation function?
    """
    maximize = board.turn == chess.WHITE
    best_move = -float("inf")
    if not maximize:
        best_move = float("inf")

    moves = get_ordered_moves(board)
    best_move_found = moves[0]

    for move in moves:
        board.push(move)
        if board.can_claim_draw():
            value = 0.0
        else:
            value = minimax(depth - 1, board, -float("inf"), float("inf"), not maximize)
        board.pop()
        if maximize and value >= best_move:
            best_move = value
            best_move_found = move
        elif not maximize and value <= best_move:
            best_move = value
            best_move_found = move

    return best_move_found
##############################################################################################
def minimax(depth: int, board: chess.Board, alpha: float, beta: float, 
            is_maximising_player: bool) -> float:
    """
    Enhanced minimax with quiescence search.
    """
    debug_info["nodes"] += 1

    if board.is_checkmate():
        return -MATE_SCORE if is_maximising_player else MATE_SCORE
    elif board.is_game_over():
        return 0

    # When we reach depth 0, use quiescence search instead of static evaluation
    if depth == 0:
        score, nodes = quiescence_search(board, alpha, beta)
        debug_info["nodes"] += nodes
        return score

    if is_maximising_player:
        best_move = -float("inf")
        moves = get_ordered_moves(board)
        for move in moves:
            board.push(move)
            curr_move = minimax(depth - 1, board, alpha, beta, not is_maximising_player)
            if curr_move > MATE_THRESHOLD:
                curr_move -= 1
            elif curr_move < -MATE_THRESHOLD:
                curr_move += 1
            best_move = max(best_move, curr_move)
            board.pop()
            alpha = max(alpha, best_move)
            if beta <= alpha:
                return best_move
        return best_move
    else:
        best_move = float("inf")
        moves = get_ordered_moves(board)
        for move in moves:
            board.push(move)
            curr_move = minimax(depth - 1, board, alpha, beta, not is_maximising_player)
            if curr_move > MATE_THRESHOLD:
                curr_move -= 1
            elif curr_move < -MATE_THRESHOLD:
                curr_move += 1
            best_move = min(best_move, curr_move)
            board.pop()
            beta = min(beta, best_move)
            if beta <= alpha:
                return best_move
        return best_move
    
def get_ordered_moves(board: chess.Board) -> List[chess.Move]:
    """
    Get legal moves.
    Attempt to sort moves by best to worst.
    Use piece values (and positional gains/losses) to weight captures.
    """
    end_game = check_end_game(board)

    def orderer(move):
        return move_value(board, move, end_game)

    in_order = sorted(
        board.legal_moves, key=orderer, reverse=(board.turn == chess.WHITE)
    )
    return list(in_order)
##############################################################################################
