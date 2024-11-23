import pygame
import chess
import chess.engine
import chess.pgn
import time
import os
from datetime import datetime
from movegeneration import next_move, debug_info
from evaluate import evaluate_board
from pgn_handler import PGNHandler

class GameSaver:
    def __init__(self, save_directory="saved_games"):
        self.save_directory = save_directory
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
    
    def save_game(self, board, white_name="MyEngine", black_name="Stockfish", result=None, stockfish_elo=None):
        game = chess.pgn.Game()
        
        game.headers["Event"] = "Training Game vs Stockfish"
        game.headers["Site"] = "Local Computer"
        game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        game.headers["Round"] = "1"
        game.headers["White"] = white_name
        game.headers["Black"] = black_name
        game.headers["Result"] = result or "*"
        if stockfish_elo:
            game.headers["BlackElo"] = str(stockfish_elo)
            game.headers["WhiteElo"] = "?"
        
        node = game
        for move in board.move_stack:
            node = node.add_variation(move)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_{white_name}_vs_{black_name}{stockfish_elo}_{timestamp}.pgn"
        filepath = os.path.join(self.save_directory, filename)
        
        with open(filepath, "w") as f:
            print(game, file=f, end="\n\n")
        
        return filepath

class VisualEngineMatch:
    def __init__(self, width=1200, height=800):
        pygame.init()
        self.width = width
        self.height = height
        self.board_size = 800
        self.square_size = self.board_size // 8
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Chess Engine Match")
        
        # Initialize PGN handler
        self.pgn_handler = PGNHandler("stockfish_matches")
        
        # Board state
        self.board = chess.Board()
        self.last_move = None
        
        # Game control
        self.is_paused = True
        self.game_started = False
        self.game_saved = False
        
        # Engine settings
        STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
        self.stockfish = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self.stockfish_elo = 1500
        
        # Add move history tracking
        self.move_history = []
        self.current_move_index = 0
        
        # Initialize colors and styles
        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.HIGHLIGHT = (130, 151, 105)
        self.BUTTON_COLOR = (200, 200, 200)
        self.BUTTON_HOVER_COLOR = (180, 180, 180)
        
        # Button dimensions and positions
        button_width = 120
        button_height = 40
        button_x = self.board_size + 50
        base_button_y = 400
        spacing = 50
        
        # Create buttons
        self.start_button = pygame.Rect(button_x, base_button_y, button_width, button_height)
        self.save_button = pygame.Rect(button_x, base_button_y + spacing, button_width, button_height)
        self.prev_button = pygame.Rect(button_x, base_button_y + spacing * 2, button_width, button_height)
        self.next_button = pygame.Rect(button_x, base_button_y + spacing * 3, button_width, button_height)
        
        # Font initialization
        self.font = pygame.font.SysFont('Arial', 20)
        self.large_font = pygame.font.SysFont('Arial', 24)
        
        # Evaluation bar
        self.eval_bar_width = 40
        self.eval_bar_height = self.height - 100
        self.eval_bar_x = self.board_size + 50
        self.eval_bar_y = 50
        self.current_eval = 0
        self.smooth_eval = 0
        
        # Last move information
        self.last_move_from_book = False

        # Load pieces
        self.pieces = {}
        self.load_pieces()

        # Add book move tracking
        self.last_move_from_book = False
        
        # Update font initialization if not already present
        self.font = pygame.font.SysFont('Arial', 20)
        self.large_font = pygame.font.SysFont('Arial', 24)
        
        # Add move history tracking
        self.move_history = []  # List of tuples (move, is_book_move)

    def load_pieces(self):
        piece_mapping = {
            'P': 'wP', 'N': 'wN', 'B': 'wB', 'R': 'wR', 'Q': 'wQ', 'K': 'wK',
            'p': 'bP', 'n': 'bN', 'b': 'bB', 'r': 'bR', 'q': 'bQ', 'k': 'bK'
        }
        
        image_directory = "/Users/danieltomaro/Documents/Projects/Chess-Engine-AI/images"
        
        for chess_symbol, filename_prefix in piece_mapping.items():
            try:
                image_path = os.path.join(image_directory, f"{filename_prefix}.png")
                self.pieces[chess_symbol] = pygame.transform.scale(
                    pygame.image.load(image_path),
                    (self.square_size, self.square_size)
                )
            except Exception as e:
                print(f"Error loading piece {filename_prefix}: {e}")

    def draw_board(self):
        for row in range(8):
            for col in range(8):
                color = self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE
                pygame.draw.rect(
                    self.screen,
                    color,
                    (col * self.square_size, row * self.square_size, 
                     self.square_size, self.square_size)
                )

    def draw_pieces(self):
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                x = chess.square_file(square) * self.square_size
                y = (7 - chess.square_rank(square)) * self.square_size
                piece_symbol = piece.symbol()
                if piece_symbol in self.pieces:
                    self.screen.blit(self.pieces[piece_symbol], (x, y))

    def draw_last_move(self):
        if self.last_move:
            for square in [self.last_move.from_square, self.last_move.to_square]:
                file = chess.square_file(square)
                rank = 7 - chess.square_rank(square)
                pygame.draw.rect(
                    self.screen,
                    self.HIGHLIGHT,
                    (file * self.square_size, rank * self.square_size,
                     self.square_size, self.square_size),
                    3
                )

    def draw_eval_bar(self):
        # Draw background
        pygame.draw.rect(
            self.screen,
            (128, 128, 128),
            (self.eval_bar_x, self.eval_bar_y, 
             self.eval_bar_width, self.eval_bar_height)
        )

        # Smooth out the evaluation
        self.smooth_eval = self.smooth_eval * 0.9 + self.current_eval * 0.1

        # Calculate the height of the white portion
        eval_value = self.smooth_eval
        max_eval = 1000
        eval_percentage = 50 + (eval_value / max_eval) * 50
        eval_percentage = max(0, min(100, eval_percentage))
        
        white_height = (eval_percentage / 100) * self.eval_bar_height
        
        # Draw white's portion
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            (self.eval_bar_x, 
             self.eval_bar_y + self.eval_bar_height - white_height,
             self.eval_bar_width, 
             white_height)
        )

        # Draw black's portion
        pygame.draw.rect(
            self.screen,
            (0, 0, 0),
            (self.eval_bar_x,
             self.eval_bar_y,
             self.eval_bar_width,
             self.eval_bar_height - white_height)
        )

        # Draw centerline
        pygame.draw.line(
            self.screen,
            (128, 128, 128),
            (self.eval_bar_x, self.eval_bar_y + self.eval_bar_height // 2),
            (self.eval_bar_x + self.eval_bar_width, self.eval_bar_y + self.eval_bar_height // 2),
            2
        )

        # Draw evaluation text
        eval_text = f"{self.smooth_eval/100:+.2f}"
        text = self.font.render(eval_text, True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.eval_bar_x + self.eval_bar_width//2, 
                                        self.eval_bar_y - 25))
        
        # Draw text background
        pygame.draw.rect(self.screen, (255, 255, 255), text_rect.inflate(10, 4))
        self.screen.blit(text, text_rect)

    def draw_buttons(self):
        mouse_pos = pygame.mouse.get_pos()
        buttons = [
            (self.start_button, "Start" if not self.game_started else ("Pause" if not self.is_paused else "Resume")),
            (self.save_button, "Save PGN"),
            (self.prev_button, "← Previous"),
            (self.next_button, "Next →")
        ]
        
        for button, text in buttons:
            # Change color if mouse is hovering over button
            color = self.BUTTON_HOVER_COLOR if button.collidepoint(mouse_pos) else self.BUTTON_COLOR
            pygame.draw.rect(self.screen, color, button)
            pygame.draw.rect(self.screen, (100, 100, 100), button, 2)  # Button border
            
            text_surf = self.font.render(text, True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=button.center)
            self.screen.blit(text_surf, text_rect)

    def draw_game_info(self):
        info_x = self.board_size + 150
        info_y = 50
        spacing = 30

        # Draw move number
        move_text = f"Move: {len(self.board.move_stack) // 2 + 1}"
        text = self.font.render(move_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y))
        
        # Draw turn indicator
        turn_text = "White to move" if self.board.turn else "Black to move"
        text = self.font.render(turn_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y + spacing))
        
        # Draw engine info
        engine_text = f"Stockfish ELO: {self.stockfish_elo}"
        text = self.font.render(engine_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y + spacing * 2))
        
        # Draw game status
        status_text = "Game Paused" if self.is_paused else "Game Running"
        text = self.font.render(status_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y + spacing * 3))

        if self.last_move:
            last_move_text = f"Last move: {self.last_move}"
            text = self.font.render(last_move_text, True, (0, 0, 0))
            self.screen.blit(text, (info_x, info_y + spacing * 4))

    def draw(self):
        """Update display with all components."""
        self.screen.fill((255, 255, 255))
        self.draw_board()
        self.draw_last_move()
        self.draw_pieces()
        self.draw_eval_bar()
        self.draw_game_info()
        self.draw_buttons()
        self.draw_move_history()
        pygame.display.flip()
    
    def draw_move_history(self):
        """Draw the move history panel."""
        history_x = self.board_size + 200
        history_y = 400
        spacing = 25
        
        title = self.font.render("Move History:", True, (0, 0, 0))
        self.screen.blit(title, (history_x, history_y - spacing))
        
        # Display last 15 moves
        start_idx = max(0, len(self.move_history) - 15)
        for i, (move, is_book) in enumerate(self.move_history[start_idx:]):
            move_number = start_idx + i + 1
            player = "Engine" if move_number % 2 == 1 else "Stockfish"
            move_text = f"{move_number}. {player}: {move}"
            color = (0, 128, 0) if is_book else (0, 0, 0)
            text = self.font.render(move_text, True, color)
            self.screen.blit(text, (history_x, history_y + spacing * i))

    def handle_click(self, pos):
        """Handle mouse clicks on buttons."""
        try:
            if self.start_button.collidepoint(pos):
                if not self.game_started:
                    self.game_started = True
                    self.is_paused = False
                    print("Game Started!")
                else:
                    self.is_paused = not self.is_paused
                    print("Game Paused!" if self.is_paused else "Game Resumed!")
                return True
                
            elif self.save_button.collidepoint(pos):
                # Enhanced save functionality with error handling
                try:
                    result = "*"  # Default result for ongoing games
                    if self.board.is_game_over():
                        if self.board.is_checkmate():
                            result = "1-0" if self.board.turn == chess.BLACK else "0-1"
                        else:
                            result = "1/2-1/2"
                    
                    headers = {
                        "Event": "Engine vs Stockfish Match",
                        "Site": "Local Computer",
                        "Date": datetime.now().strftime("%Y.%m.%d"),
                        "White": "MyEngine",
                        "Black": f"Stockfish (ELO: {self.stockfish_elo})",
                        "Result": result,
                        "TimeControl": "1+0",
                        "Opening": "Perfect2021 Book",  # Add book information
                        "WhiteElo": "?",
                        "BlackElo": str(self.stockfish_elo)
                    }
                    
                    filepath = self.pgn_handler.save_game(self.board, headers)
                    print(f"Game successfully saved to: {filepath}")
                    
                    # Read back the saved file to verify
                    with open(filepath, 'r') as f:
                        content = f.read()
                        print(f"Verified save - file contains {len(content)} characters")
                    
                    return True
                    
                except Exception as e:
                    print(f"Error saving game: {str(e)}")
                    return False
                
            elif self.prev_button.collidepoint(pos):
                self.navigate_moves(-1)
                return True
                
            elif self.next_button.collidepoint(pos):
                self.navigate_moves(1)
                return True
                
            return False
            
        except Exception as e:
            print(f"Error in handle_click: {str(e)}")
            return False

    def show_game_over(self):
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill((255, 255, 255))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        result = None
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            result = "0-1" if winner == "Black" else "1-0"
            message = f"{winner} wins by checkmate!"
        else:
            result = "1/2-1/2"
            message = "Game drawn!"

        # Save the game if it hasn't been saved yet
        if not self.game_saved:
            saved_path = self.game_saver.save_game(
                self.board,
                white_name="MyEngine",
                black_name="Stockfish",
                result=result,
                stockfish_elo=self.stockfish_elo
            )
            print(f"Game saved to: {saved_path}")
            self.game_saved = True

        text = self.large_font.render(message, True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.width/2, self.height/2))
        self.screen.blit(text, text_rect)
        pygame.display.flip()
    
    def draw_pgn_controls(self):
        """Draw PGN control buttons and move history."""
        # Draw buttons
        buttons = [
            (self.save_button, "Save PGN"),
            (self.prev_button, "← Previous"),
            (self.next_button, "Next →"),
            (self.pause_button, "Pause" if not self.is_paused else "Resume")
        ]
        
        for button, text in buttons:
            pygame.draw.rect(self.screen, (200, 200, 200), button)
            text_surf = self.font.render(text, True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=button.center)
            self.screen.blit(text_surf, text_rect)
        
        # Draw move history
        history_x = self.board_size + 200
        history_y = 400
        spacing = 20
        
        title = self.font.render("Move History:", True, (0, 0, 0))
        self.screen.blit(title, (history_x, history_y))
        
        # Display last 15 moves
        start_idx = max(0, len(self.move_history) - 15)
        for i, (move, is_book) in enumerate(self.move_history[start_idx:]):
            move_number = start_idx + i + 1
            player = "Engine" if move_number % 2 == 1 else "Stockfish"
            move_text = f"{move_number}. {player}: {move}"
            color = (0, 128, 0) if is_book else (0, 0, 0)
            text = self.font.render(move_text, True, color)
            self.screen.blit(text, (history_x, history_y + spacing * (i + 1)))

    def handle_pgn_button_click(self, pos):
        """Handle clicks on PGN control buttons."""
        if self.save_button.collidepoint(pos):
            headers = {
                "Event": "Engine vs Stockfish Match",
                "Site": "Local Computer",
                "Date": datetime.now().strftime("%Y.%m.%d"),
                "White": "MyEngine",
                "Black": f"Stockfish (ELO: {self.stockfish_elo})",
                "TimeControl": "1+0"
            }
            filepath = self.pgn_handler.save_game(self.board, headers)
            print(f"Game saved to: {filepath}")
            
        elif self.prev_button.collidepoint(pos):
            self.navigate_moves(-1)
            
        elif self.next_button.collidepoint(pos):
            self.navigate_moves(1)
            
        elif self.pause_button.collidepoint(pos):
            self.is_paused = not self.is_paused

    def navigate_moves(self, direction: int):
        """Navigate through move history."""
        if not self.move_history:
            return
            
        target_index = self.current_move_index + direction
        
        if 0 <= target_index <= len(self.move_history):
            # Reset board to starting position
            self.board = chess.Board()
            self.current_move_index = 0
            
            # Replay moves up to target index
            for i in range(target_index):
                move = chess.Move.from_uci(self.move_history[i][0])  # [0] is the move, [1] is is_book
                self.board.push(move)
                self.current_move_index = i + 1

    def play_match(self, stockfish_elo=1500):
        """Main game loop."""
        self.stockfish_elo = stockfish_elo
        self.stockfish.configure({"UCI_LimitStrength": True, "UCI_Elo": stockfish_elo})
        self.move_history = []
        self.current_move_index = 0
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)

            if self.game_started and not self.is_paused and not self.board.is_game_over():
                # Make moves
                if self.board.turn == chess.WHITE:
                    # Our engine's move
                    debug_info.clear()
                    move = next_move(3, self.board)
                    is_book_move = debug_info.get("book_move", False)
                else:
                    # Stockfish's move
                    result = self.stockfish.play(self.board, chess.engine.Limit(time=1.0))
                    move = result.move
                    is_book_move = False

                # Make the move and record it
                self.board.push(move)
                self.move_history.append((move.uci(), is_book_move))
                self.current_move_index = len(self.move_history)
                self.last_move = move
                
                # Update evaluation
                self.current_eval = evaluate_board(self.board)
                
                # Delay to make the game viewable
                time.sleep(1)
            
            self.draw()
            
            if self.board.is_game_over():
                self.is_paused = True
                self.show_game_over()
            
            clock.tick(60)

        pygame.quit()
        self.stockfish.quit()
        
    def draw_game_info(self):
        info_x = self.board_size + 150
        info_y = 50
        spacing = 30

        # Draw move number
        move_text = f"Move: {len(self.board.move_stack) // 2 + 1}"
        text = self.font.render(move_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y))
        
        # Draw turn indicator
        turn_text = "MyEngine" if self.board.turn else "Stockfish"
        text = self.font.render(f"{turn_text} to move", True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y + spacing))
        
        # Draw engine info
        engine_text = f"Stockfish ELO: {self.stockfish_elo}"
        text = self.font.render(engine_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y + spacing * 2))
        
        # Draw game status
        status_text = "Game Paused" if self.is_paused else "Game Running"
        text = self.font.render(status_text, True, (0, 0, 0))
        self.screen.blit(text, (info_x, info_y + spacing * 3))

        # Draw last move with book move indicator
        if self.last_move:
            move_source = " (Book Move)" if self.last_move_from_book else ""
            last_move_text = f"Last move: {self.last_move}{move_source}"
            text_color = (0, 128, 0) if self.last_move_from_book else (0, 0, 0)
            text = self.font.render(last_move_text, True, text_color)
            self.screen.blit(text, (info_x, info_y + spacing * 4))

        # Draw last few moves of the game
        if self.move_history:
            history_text = "Recent moves:"
            text = self.font.render(history_text, True, (0, 0, 0))
            self.screen.blit(text, (info_x, info_y + spacing * 5))
            
            # Show last 5 moves
            for i, (move, is_book) in enumerate(self.move_history[-5:]):
                move_text = f"{len(self.move_history)-4+i}. {move}"
                if is_book:
                    move_text += " (Book)"
                text_color = (0, 128, 0) if is_book else (0, 0, 0)
                text = self.font.render(move_text, True, text_color)
                self.screen.blit(text, (info_x, info_y + spacing * (6 + i)))

def main():
    print("Visual Engine Match")
    print("=" * 50)
    
    while True:
        try:
            elo = int(input("Enter Stockfish ELO (1000-3000): "))
            if 1000 <= elo <= 3000:
                break
            print("Please enter an ELO between 1000 and 3000")
        except ValueError:
            print("Please enter a valid number")

    match = VisualEngineMatch()
    match.play_match(stockfish_elo=elo)

if __name__ == "__main__":
    main()
