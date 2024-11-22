import pygame
import chess
import chess.engine
import time
import os
from movegeneration import next_move
from evaluate import evaluate_board

class VisualEngineMatch:
    def __init__(self, width=1200, height=800):
        pygame.init()
        self.width = width
        self.height = height
        self.board_size = 800
        self.square_size = self.board_size // 8
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Chess Engine Match")
        
        # Board state
        self.board = chess.Board()
        self.last_move = None
        
        # Game control
        self.is_paused = True
        self.game_started = False
        
        # Engine settings
        STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
        self.stockfish = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self.stockfish_elo = 1500
        
        # Colors
        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.HIGHLIGHT = (130, 151, 105)
        self.LAST_MOVE = (255, 255, 0, 128)
        
        # Evaluation bar
        self.eval_bar_width = 40
        self.eval_bar_height = self.height - 100  # Slightly shorter than window
        self.eval_bar_x = self.board_size + 50
        self.eval_bar_y = 50  # Start slightly below top
        self.current_eval = 0
        self.smooth_eval = 0
        
        # Buttons
        self.button_width = 150
        self.button_height = 50
        self.start_button = pygame.Rect(
            self.board_size + 150, 
            self.height - 150, 
            self.button_width, 
            self.button_height
        )
        
        # Load pieces
        self.pieces = {}
        self.load_pieces()
        
        # Font
        self.font = pygame.font.SysFont('Arial', 20)
        self.large_font = pygame.font.SysFont('Arial', 24)

    def load_pieces(self):
        piece_mapping = {
            'P': 'wP', 'N': 'wN', 'B': 'wB', 'R': 'wR', 'Q': 'wQ', 'K': 'wK',
            'p': 'bP', 'n': 'bN', 'b': 'bB', 'r': 'bR', 'q': 'bQ', 'k': 'bK'
        }
        
        image_directory = "/Users/danieltomaro/Documents/Projects/Chess/images"
        
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

    def draw_controls(self):
        # Draw start/stop button
        pygame.draw.rect(self.screen, (200, 200, 200), self.start_button)
        button_text = "Start" if self.is_paused else "Pause"
        text = self.large_font.render(button_text, True, (0, 0, 0))
        text_rect = text.get_rect(center=self.start_button.center)
        self.screen.blit(text, text_rect)

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

        # Draw last move if exists
        if self.last_move:
            last_move_text = f"Last move: {self.last_move}"
            text = self.font.render(last_move_text, True, (0, 0, 0))
            self.screen.blit(text, (info_x, info_y + spacing * 4))

    def draw(self):
        self.screen.fill((255, 255, 255))
        self.draw_board()
        self.draw_last_move()
        self.draw_pieces()
        self.draw_eval_bar()
        self.draw_controls()
        self.draw_game_info()
        pygame.display.flip()

    def handle_click(self, pos):
        if self.start_button.collidepoint(pos):
            self.is_paused = not self.is_paused
            self.game_started = True
            return True
        return False

    def play_match(self, stockfish_elo=1500):
        self.stockfish_elo = stockfish_elo
        self.stockfish.configure({"UCI_LimitStrength": True, "UCI_Elo": stockfish_elo})
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)

            if not self.is_paused and self.game_started and not self.board.is_game_over():
                # Make moves
                if self.board.turn == chess.WHITE:
                    # Our engine's move
                    move = next_move(3, self.board)
                else:
                    # Stockfish's move
                    result = self.stockfish.play(self.board, chess.engine.Limit(time=1.0))
                    move = result.move

                # Make the move
                self.board.push(move)
                self.last_move = move
                
                # Update evaluation
                self.current_eval = evaluate_board(self.board)
                
                # Delay to make the game viewable
                time.sleep(1)
            
            # Always draw the current position
            self.draw()
            
            if self.board.is_game_over():
                self.is_paused = True
                self.show_game_over()
            
            clock.tick(60)

        pygame.quit()
        self.stockfish.quit()

    def show_game_over(self):
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill((255, 255, 255))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            message = f"{winner} wins by checkmate!"
        else:
            message = "Game drawn!"

        text = self.large_font.render(message, True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.width/2, self.height/2))
        self.screen.blit(text, text_rect)
        pygame.display.flip()

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