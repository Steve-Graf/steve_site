import random
import string


def generate_share_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase, k=length))


def assign_tile_ids(texts: list[str]) -> list[dict]:
    return [
        {"id": i, "text": text, "completed": False, "photos": []}
        for i, text in enumerate(texts)
    ]


def build_player_tile_ids(tile_pool: list[dict], board_size: int) -> list[int]:
    cells = board_size * board_size
    return random.sample([t["id"] for t in tile_pool], cells)


def tile_pool_by_id(tile_pool: list[dict]) -> dict[int, dict]:
    return {t["id"]: t for t in tile_pool}


def resolve_board_tiles(pool_by_id: dict[int, dict], tile_ids: list[int]) -> list[dict]:
    return [pool_by_id[tid] for tid in tile_ids]


def reshape_2d(flat: list, board_size: int) -> list[list]:
    return [flat[i * board_size:(i + 1) * board_size] for i in range(board_size)]


def check_bingo(tiles: list[dict], board_size: int) -> bool:
    state = reshape_2d([t["completed"] for t in tiles], board_size)

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


def user_in_game(db, game_doc, user) -> bool:
    if game_doc.get("owner_id") == user["id"]:
        return True

    existing = (
        db.collection("player_boards")
        .where("player_id", "==", user["id"])
        .where("game_id", "==", game_doc.id)
        .limit(1)
        .get()
    )
    return bool(existing)
