from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore
from ..extensions import get_db
from ..services.bingo_service import (
    generate_share_code,
    assign_tile_ids,
    build_player_tile_ids,
    tile_pool_by_id,
    resolve_board_tiles,
    reshape_2d,
    check_bingo,
)
from ..services.photo_service import save_tile_photo, delete_tile_photo, delete_all_photos, with_photo_urls

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
        "tile_pool": assign_tile_ids(tile_pool),
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

    pb_docs = db.collection("player_boards").where("game_id", "==", game_id).stream()
    for pb in pb_docs:
        pb.reference.delete()

    delete_all_photos(game_id)
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

    tile_ids = build_player_tile_ids(game["tile_pool"], game["board_size"])
    _, pb_ref = db.collection("player_boards").add({
        "player_id": user["id"],
        "game_id": game_id,
        "tile_ids": tile_ids,
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

    game_id = pb_doc.get("game_id")
    game_doc = db.collection("games").document(game_id).get()
    if not game_doc.exists:
        return jsonify({"error": "Game not found"}), 404

    size = game_doc.get("board_size")
    pool_by_id = tile_pool_by_id(game_doc.get("tile_pool"))
    tiles = [
        with_photo_urls(game_id, t)
        for t in resolve_board_tiles(pool_by_id, pb_doc.get("tile_ids"))
    ]

    return jsonify({
        "id": pb_doc.id,
        "game_id": game_id,
        "tiles": reshape_2d(tiles, size),
        "has_bingo": check_bingo(tiles, size),
    })


# --- Shared game tiles ---

def _find_tile(tile_pool, tile_id):
    for tile in tile_pool:
        if tile["id"] == tile_id:
            return tile
    return None


def _load_tile_for_user(db, game_id, tile_id, user):
    """Loads the game + the requester's own player_board, requiring the tile
    to actually be on that player's board (editing a shared tile is only
    allowed for players who were dealt it)."""
    game_doc = db.collection("games").document(game_id).get()
    if not game_doc.exists:
        return None, None, (jsonify({"error": "Not found"}), 404)

    if _find_tile(game_doc.get("tile_pool"), tile_id) is None:
        return None, None, (jsonify({"error": "Tile not found"}), 404)

    pb_docs = (
        db.collection("player_boards")
        .where("player_id", "==", user["id"])
        .where("game_id", "==", game_id)
        .limit(1)
        .get()
    )
    if not pb_docs or tile_id not in pb_docs[0].get("tile_ids"):
        return None, None, (jsonify({"error": "Forbidden"}), 403)

    return game_doc, pb_docs[0], None


@firestore.transactional
def _toggle_tile_txn(transaction, game_ref, tile_id):
    snapshot = game_ref.get(transaction=transaction)
    tile_pool = list(snapshot.get("tile_pool"))
    tile = _find_tile(tile_pool, tile_id)

    tile["completed"] = not tile["completed"]
    removed_photos = []
    if not tile["completed"] and tile["photos"]:
        removed_photos = tile["photos"]
        tile["photos"] = []

    transaction.update(game_ref, {"tile_pool": tile_pool})
    return tile_pool, removed_photos


@firestore.transactional
def _append_tile_photo_txn(transaction, game_ref, tile_id, filename):
    snapshot = game_ref.get(transaction=transaction)
    tile_pool = list(snapshot.get("tile_pool"))
    tile = _find_tile(tile_pool, tile_id)

    tile["photos"] = [*tile["photos"], {"filename": filename}]
    tile["completed"] = True

    transaction.update(game_ref, {"tile_pool": tile_pool})
    return tile_pool


@firestore.transactional
def _remove_tile_photo_txn(transaction, game_ref, tile_id, filename):
    snapshot = game_ref.get(transaction=transaction)
    tile_pool = list(snapshot.get("tile_pool"))
    tile = _find_tile(tile_pool, tile_id)

    if not any(p["filename"] == filename for p in tile["photos"]):
        return tile_pool, False

    tile["photos"] = [p for p in tile["photos"] if p["filename"] != filename]

    transaction.update(game_ref, {"tile_pool": tile_pool})
    return tile_pool, True


def _respond_with_tile(game_id, tile_id, tile_pool, board_size, pb_doc):
    pool_by_id = tile_pool_by_id(tile_pool)
    board_tiles = resolve_board_tiles(pool_by_id, pb_doc.get("tile_ids"))
    has_bingo = check_bingo(board_tiles, board_size)
    tile = with_photo_urls(game_id, pool_by_id[tile_id])
    return jsonify({"tile": tile, "has_bingo": has_bingo})


@bingo_api_bp.route("/games/<game_id>/tiles/<int:tile_id>/toggle", methods=["PATCH"])
def toggle_tile(game_id, tile_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    game_doc, pb_doc, err = _load_tile_for_user(db, game_id, tile_id, user)
    if err:
        return err

    game_ref = db.collection("games").document(game_id)
    tile_pool, removed_photos = _toggle_tile_txn(db.transaction(), game_ref, tile_id)
    for photo in removed_photos:
        delete_tile_photo(game_id, photo["filename"])

    return _respond_with_tile(game_id, tile_id, tile_pool, game_doc.get("board_size"), pb_doc)


@bingo_api_bp.route("/games/<game_id>/tiles/<int:tile_id>/photo", methods=["POST"])
def upload_tile_photo(game_id, tile_id):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    game_doc, pb_doc, err = _load_tile_for_user(db, game_id, tile_id, user)
    if err:
        return err

    photo = request.files.get("photo")
    if not photo or not photo.filename:
        return jsonify({"error": "No photo provided"}), 400

    try:
        filename = save_tile_photo(game_id, tile_id, photo)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    game_ref = db.collection("games").document(game_id)
    tile_pool = _append_tile_photo_txn(db.transaction(), game_ref, tile_id, filename)

    return _respond_with_tile(game_id, tile_id, tile_pool, game_doc.get("board_size"), pb_doc)


@bingo_api_bp.route("/games/<game_id>/tiles/<int:tile_id>/photos/<filename>", methods=["DELETE"])
def delete_tile_photo_route(game_id, tile_id, filename):
    user, err = require_auth()
    if err:
        return err

    db = get_db()
    game_doc, pb_doc, err = _load_tile_for_user(db, game_id, tile_id, user)
    if err:
        return err

    game_ref = db.collection("games").document(game_id)
    tile_pool, removed = _remove_tile_photo_txn(db.transaction(), game_ref, tile_id, filename)
    if not removed:
        return jsonify({"error": "Photo not found"}), 404
    delete_tile_photo(game_id, filename)

    return _respond_with_tile(game_id, tile_id, tile_pool, game_doc.get("board_size"), pb_doc)
