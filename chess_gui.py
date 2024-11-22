import pygame
import chess
import os
import time
from movegeneration import next_move
from evaluate import evaluate_board

class ChessGUI:
    def __init__(self, width=1000, height=800):
        pygame.init()
        self.width = width
        self.height = height
        self.board_size = 800
        self.square_size = self.board_size // 8
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Chess Engine")
        
        # Evaluation bar parameters
        self.eval_bar_width = 30
        self.eval_bar_height = self.board_size
        self.eval_bar_x = self.board_size + 50
        self.eval_bar_y = 0
        self.current_eval = 0
        self.smooth_eval = 0
        
        # Initialize board and game state
        self.board = chess.Board()
        self.selected_square = None
        self.valid_moves = []
        self.player_color = chess.WHITE
        self.ai_thinking = False
        
        # Animation and timing control
        self.last_move_time = time.time()
        self.move_delay = 1.0
        self.animation_speed = 15
        
        # Colors
        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.HIGHLIGHT = (130, 151, 105)
        self.MOVE_HINT = (187, 203, 43)
        self.WHITE_EVAL = (255, 255, 255)
        self.BLACK_EVAL = (0, 0, 0)
        
        # Game state
        self.game_over = False
        self.message = ""
        self.last_move = None
        
        # Load piece images
        self.pieces = {}
        self.load_pieces()

    def load_pieces(self):
        piece_mapping = {
            'P': 'wP',  # white pawn
            'N': 'wN',  # white knight
            'B': 'wB',  # white bishop
            'R': 'wR',  # white rook
            'Q': 'wQ',  # white queen
            'K': 'wK',  # white king
            'p': 'bP',  # black pawn
            'n': 'bN',  # black knight
            'b': 'bB',  # black bishop
            'r': 'bR',  # black rook
            'q': 'bQ',  # black queen
            'k': 'bK'   # black king
        }
        
        image_directory = "/Users/danieltomaro/Documents/Projects/Chess-Engine-AI/images"
        
        for chess_symbol, filename_prefix in piece_mapping.items():
            try:
                image_path = os.path.join(image_directory, f"{filename_prefix}.png")
                print(f"Loading image: {image_path}")
                self.pieces[chess_symbol] = pygame.transform.scale(
                    pygame.image.load(image_path),
                    (self.square_size, self.square_size)
                )
            except pygame.error as e:
                print(f"Error loading piece image {image_path}: {e}")
            except Exception as e:
                print(f"Unexpected error loading {image_path}: {e}")

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

    def draw_highlights(self):
        if self.selected_square is not None:
            file = chess.square_file(self.selected_square)
            rank = 7 - chess.square_rank(self.selected_square)
            pygame.draw.rect(
                self.screen,
                self.HIGHLIGHT,
                (file * self.square_size, rank * self.square_size,
                 self.square_size, self.square_size)
            )
            
            for move in self.valid_moves:
                if move.from_square == self.selected_square:
                    file = chess.square_file(move.to_square)
                    rank = 7 - chess.square_rank(move.to_square)
                    pygame.draw.circle(
                        self.screen,
                        self.MOVE_HINT,
                        (file * self.square_size + self.square_size // 2,
                         rank * self.square_size + self.square_size // 2),
                        self.square_size // 6
                    )

    def draw_eval_bar(self):
        # Draw background
        pygame.draw.rect(
            self.screen,
            (128, 128, 128),
            (self.eval_bar_x, self.eval_bar_y, self.eval_bar_width, self.eval_bar_height)
        )

        # Smooth out the evaluation change
        self.smooth_eval = self.smooth_eval * 0.9 + self.current_eval * 0.1

        # Calculate the height of the white portion
        eval_value = self.smooth_eval
        max_eval = 2000
        eval_percentage = 50 + (eval_value / max_eval) * 50
        eval_percentage = max(0, min(100, eval_percentage))
        
        white_height = (eval_percentage / 100) * self.eval_bar_height
        
        # Draw white's portion (from bottom)
        pygame.draw.rect(
            self.screen,
            self.WHITE_EVAL,
            (self.eval_bar_x, 
             self.eval_bar_y + self.eval_bar_height - white_height,
             self.eval_bar_width, 
             white_height)
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
        font = pygame.font.SysFont('Arial', 14)
        eval_text = f"{self.smooth_eval/100:+.2f}" if abs(self.smooth_eval) < float('inf') else "M8"
        text = font.render(eval_text, True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.eval_bar_x + self.eval_bar_width // 2, 
                                        self.height // 2))
        
        # Draw text background
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            text_rect.inflate(10, 4)
        )
        self.screen.blit(text, text_rect)

    def update_evaluation(self):
        if not self.game_over:
            self.current_eval = evaluate_board(self.board)

    def draw_game_over(self):
        if self.game_over:
            font = pygame.font.SysFont('Arial', 32)
            text = font.render(self.message, True, (0, 0, 0))
            text_rect = text.get_rect(center=(self.width/2, self.height/2))
            
            overlay = pygame.Surface((self.width, self.height))
            overlay.fill((255, 255, 255))
            overlay.set_alpha(180)
            self.screen.blit(overlay, (0, 0))
            
            self.screen.blit(text, text_rect)

    def draw_last_move(self):
        if self.last_move:
            file_from = chess.square_file(self.last_move.from_square)
            rank_from = 7 - chess.square_rank(self.last_move.from_square)
            pygame.draw.rect(
                self.screen,
                (255, 255, 0, 128),
                (file_from * self.square_size, rank_from * self.square_size,
                 self.square_size, self.square_size),
                3
            )
            
            file_to = chess.square_file(self.last_move.to_square)
            rank_to = 7 - chess.square_rank(self.last_move.to_square)
            pygame.draw.rect(
                self.screen,
                (255, 255, 0, 128),
                (file_to * self.square_size, rank_to * self.square_size,
                 self.square_size, self.square_size),
                3
            )

    def get_square_from_pos(self, pos):
        x, y = pos
        file = x // self.square_size
        rank = 7 - (y // self.square_size)
        return chess.square(file, rank)

    def handle_click(self, pos):
        if self.game_over or self.ai_thinking or self.board.turn != self.player_color:
            return

        current_time = time.time()
        if current_time - self.last_move_time < self.move_delay:
            return

        square = self.get_square_from_pos(pos)
        
        if self.selected_square is not None:
            move = chess.Move(self.selected_square, square)
            if any(m.from_square == self.selected_square and m.to_square == square 
                  for m in self.valid_moves):
                if (self.board.piece_at(self.selected_square).piece_type == chess.PAWN and
                    ((self.player_color == chess.WHITE and chess.square_rank(square) == 7) or
                     (self.player_color == chess.BLACK and chess.square_rank(square) == 0))):
                    move = chess.Move(self.selected_square, square, chess.QUEEN)
                
                self.board.push(move)
                self.last_move = move
                self.last_move_time = current_time
                self.selected_square = None
                self.valid_moves = []
                
                # Update evaluation after player move
                self.update_evaluation()
                
                if self.board.is_game_over():
                    self.game_over = True
                    self.message = self.get_game_over_message()
                else:
                    self.ai_thinking = True
            else:
                self.selected_square = None
                self.valid_moves = []
        else:
            piece = self.board.piece_at(square)
            if piece and piece.color == self.player_color:
                self.selected_square = square
                self.valid_moves = list(self.board.legal_moves)

    def make_ai_move(self):
        if self.ai_thinking and not self.game_over:
            current_time = time.time()
            if current_time - self.last_move_time < self.move_delay:
                return

            move = next_move(3, self.board)
            self.board.push(move)
            self.last_move = move
            self.last_move_time = current_time
            self.ai_thinking = False
            
            # Update evaluation after AI move
            self.update_evaluation()
            
            if self.board.is_game_over():
                self.game_over = True
                self.message = self.get_game_over_message()

    def get_game_over_message(self):
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"{winner} wins by checkmate!"
        elif self.board.is_stalemate():
            return "Game drawn by stalemate"
        elif self.board.is_insufficient_material():
            return "Game drawn by insufficient material"
        elif self.board.is_fifty_moves():
            return "Game drawn by fifty-move rule"
        elif self.board.is_repetition():
            return "Game drawn by repetition"
        return "Game Over"

    def draw(self):
        self.draw_board()
        self.draw_last_move()
        self.draw_highlights()
        self.draw_pieces()
        self.draw_eval_bar()  # Added evaluation bar
        self.draw_game_over()
        pygame.display.flip()

def main():
    gui = ChessGUI()
    clock = pygame.time.Clock()
    running = True

    # Initial evaluation
    gui.update_evaluation()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    gui.handle_click(event.pos)

        gui.make_ai_move()
        gui.draw()
        clock.tick(gui.animation_speed)

    pygame.quit()

if __name__ == "__main__":
    main()