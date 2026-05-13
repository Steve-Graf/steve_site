from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from ..extensions import get_db
from ..services.bingo_service import (
    generate_share_code,
    build_player_layout,
    empty_completion_state,
    reshape_2d,
    check_bingo,
)

bingo_api_bp = Blueprint("bingo_api", __name__)


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    doc = get_db().collection("users").document(uid).get()
    if not doc.exists:
        return None
    return {"id": uid, **doc.to_dict()}


def require_auth():
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Authentication required"}), 401)
    return user, None


# --- Boards ---

@bingo_api_bp.route("/boards", methods=["POST"])
def create_board():
    user, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    board_size = data.get("board_size")
    tile_pool = data.get("tile_pool", [])

    if not title or len(title) > 255:
        return jsonify({"error": "Title is required and must be under 255 characters"}), 400
    if board_size not in (3, 4, 5):
        return jsonify({"error": "Board size must be 3, 4, or 5"}), 400
    if not isinstance(tile_pool, list) or len(tile_pool) < board_size ** 2:
        return jsonify({"error": f"Tile pool must have at least {board_size ** 2} tiles"}), 400

    tile_pool = [str(t).strip() for t in tile_pool if str(t).strip()]
    if len(tile_pool) < board_size ** 2:
        return jsonify({"error": f"Tile pool must have at least {board_size ** 2} non-empty tiles"}), 400

    db = get_db()
    share_code = generate_share_code()
    while db.collection("games").where("share_code", "==", share_code).limit(1).get():
        share_code = generate_share_code()

    _, game_ref = db.collection("games").add({
        "owner_id": user["id"],
        "title": title,
        "board_size": board_size,
        "tile_pool": tile_pool,
        "share_code": share_code,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    return jsonify({"id": game_ref.id, "share_code": share_code}), 201


@bingo_api_bp.route("/boards", methods=["GET"])
def list_boards():
    user, err = require_auth()
    if err:
        return err

    docs = (
        get_db()
        .collection("games")
        .where("owner_id", "==", user["id"])
        .order_by("created_at", direction="DESCENDING")
        .stream()
    )
    return jsonify([{
        "id": d.id,
        "title": d.get("title"),
        "board_size": d.get("board_size"),
        "share_code": d.get("share_code"),
        "is_active": d.get("is_active"),
        "tile_count": len(d.get("tile_pool") or []),
    } for d in docs])


@bingo_api_bp.route("/boards/<game_id>", methods=["DELETE"])
def delete_board(game_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    game_doc = db.collection("games").document(game_id).get()
    if not game_doc.exists:
        return jsonify({"error": "Not found"}), 404
    if game_doc.get("owner_id") != user["id"]:
        return jsonify({"error": "Forbidden"}), 403

    # Cascade delete all player boards for this game
    pb_docs = db.collection("player_boards").where("game_id", "==", game_id).stream()
    for pb in pb_docs:
        pb.reference.delete()

    db.collection("games").document(game_id).delete()
    return jsonify({"ok": True})


@bingo_api_bp.route("/boards/<game_id>/archive", methods=["POST"])
def archive_board(game_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    game_doc = db.collection("games").document(game_id).get()
    if not game_doc.exists:
        return jsonify({"error": "Not found"}), 404

    archived = user.get("archived_game_ids") or []
    if game_id not in archived:
        archived.append(game_id)
        db.collection("users").document(user["id"]).update({"archived_game_ids": archived})

    return jsonify({"ok": True})


@bingo_api_bp.route("/boards/<game_id>/join", methods=["POST"])
def join_board(game_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    game_doc = db.collection("games").document(game_id).get()
    if not game_doc.exists:
        return jsonify({"error": "Not found"}), 404
    game = {"id": game_doc.id, **game_doc.to_dict()}

    existing = (
        db.collection("player_boards")
        .where("player_id", "==", user["id"])
        .where("game_id", "==", game_id)
        .limit(1)
        .get()
    )
    if existing:
        return jsonify({"id": existing[0].id, "already_joined": True})

    layout = build_player_layout(game["tile_pool"], game["board_size"])
    state = empty_completion_state(game["board_size"])
    _, pb_ref = db.collection("player_boards").add({
        "player_id": user["id"],
        "game_id": game_id,
        "tile_layout": layout,
        "completion_state": state,
        "has_bingo": False,
        "created_at": datetime.now(timezone.utc),
    })
    return jsonify({"id": pb_ref.id}), 201


# --- Player Boards ---

@bingo_api_bp.route("/player-boards/<pb_id>", methods=["GET"])
def get_player_board(pb_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    pb_doc = db.collection("player_boards").document(pb_id).get()
    if not pb_doc.exists:
        return jsonify({"error": "Not found"}), 404
    if pb_doc.get("player_id") != user["id"]:
        return jsonify({"error": "Forbidden"}), 403

    game_doc = db.collection("games").document(pb_doc.get("game_id")).get()
    size = game_doc.get("board_size") if game_doc.exists else None
    flat_layout = pb_doc.get("tile_layout")
    flat_state = pb_doc.get("completion_state")
    return jsonify({
        "id": pb_doc.id,
        "game_id": pb_doc.get("game_id"),
        "tile_layout": reshape_2d(flat_layout, size) if size else flat_layout,
        "completion_state": reshape_2d(flat_state, size) if size else flat_state,
        "has_bingo": pb_doc.get("has_bingo"),
    })


@bingo_api_bp.route("/player-boards/<pb_id>/toggle", methods=["PATCH"])
def toggle_tile(pb_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    pb_doc = db.collection("player_boards").document(pb_id).get()
    if not pb_doc.exists:
        return jsonify({"error": "Not found"}), 404
    if pb_doc.get("player_id") != user["id"]:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    row = data.get("row")
    col = data.get("col")

    game_doc = db.collection("games").document(pb_doc.get("game_id")).get()
    if not game_doc.exists:
        return jsonify({"error": "Game not found"}), 404
    size = game_doc.get("board_size")

    if not isinstance(row, int) or not isinstance(col, int):
        return jsonify({"error": "row and col must be integers"}), 400
    if not (0 <= row < size and 0 <= col < size):
        return jsonify({"error": "row or col out of bounds"}), 400

    flat_state = list(pb_doc.get("completion_state"))
    flat_state[row * size + col] = not flat_state[row * size + col]
    state_2d = reshape_2d(flat_state, size)
    has_bingo = check_bingo(state_2d, size)

    db.collection("player_boards").document(pb_id).update({
        "completion_state": flat_state,
        "has_bingo": has_bingo,
    })
    return jsonify({"completion_state": state_2d, "has_bingo": has_bingo})
