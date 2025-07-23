"""
Core game logic for Tic Tac Toe: move validation, board state management, win/draw detection.

All game endpoints should call these functions to ensure consistent rules and outcomes.
"""

# PUBLIC_INTERFACE
def validate_move(board_state: str, position: int) -> bool:
    """Returns True if the given position is empty and valid (for move)."""
    if not (0 <= position <= 8):
        return False
    return board_state[position] == " "

# PUBLIC_INTERFACE
def next_player_symbol(moves_count: int) -> str:
    """Returns 'X' if moves_count is even, 'O' if odd. X always goes first."""
    return "X" if moves_count % 2 == 0 else "O"

# PUBLIC_INTERFACE
def apply_move(board_state: str, position: int, symbol: str) -> str:
    """Returns a new board_state string with the move applied."""
    board = list(board_state)
    board[position] = symbol
    return "".join(board)

# PUBLIC_INTERFACE
def get_winner(board_state: str) -> str | None:
    """Returns 'X', 'O', or None if no winner. Accepts board state as a string of len 9."""
    b = board_state
    lines = [
        (0,1,2), (3,4,5), (6,7,8),  # rows
        (0,3,6), (1,4,7), (2,5,8),  # cols
        (0,4,8), (2,4,6)            # diags
    ]
    for i, j, k in lines:
        if b[i] == b[j] == b[k] and b[i] in "XO":
            return b[i]
    return None

# PUBLIC_INTERFACE
def is_draw(board_state: str) -> bool:
    """Returns True if the board is full and there is no winner."""
    return " " not in board_state and get_winner(board_state) is None

# PUBLIC_INTERFACE
def get_game_status(board_state: str) -> str:
    """
    Returns "FINISHED" if win or draw, else "IN_PROGRESS".
    If board has empty cells and no winner: "IN_PROGRESS".
    If winner or draw: "FINISHED".
    """
    if get_winner(board_state) or is_draw(board_state):
        return "FINISHED"
    return "IN_PROGRESS"
