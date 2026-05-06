import random
import string


def generate_share_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase, k=length))


def build_player_layout(tile_pool: list[str], board_size: int) -> list[list[str]]:
    cells = board_size * board_size
    selected = random.sample(tile_pool, cells)
    return [selected[i * board_size:(i + 1) * board_size] for i in range(board_size)]


def empty_completion_state(board_size: int) -> list[list[bool]]:
    return [[False] * board_size for _ in range(board_size)]


def check_bingo(state: list[list[bool]], board_size: int) -> bool:
    # Check rows
    for row in state:
        if all(row):
            return True
    # Check columns
    for col in range(board_size):
        if all(state[row][col] for row in range(board_size)):
            return True
    # Check diagonals
    if all(state[i][i] for i in range(board_size)):
        return True
    if all(state[i][board_size - 1 - i] for i in range(board_size)):
        return True
    return False
