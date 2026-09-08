from datetime import datetime, timezone
from flask import Blueprint, render_template, session, redirect, url_for, request, abort, send_file, jsonify, Response
from ..extensions import get_db
from ..decorators import login_required
from ..services.bingo_service import (
    build_player_tile_ids,
    tile_pool_by_id,
    resolve_board_tiles,
    reshape_2d,
    check_bingo,
    user_in_game,
)
from ..services.photo_service import resolve_photo_path, with_photo_urls

bingo_pages_bp = Blueprint(
    "bingo_pages", __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/static",
)


@bingo_pages_bp.after_request
def _no_cache_for_scripts_and_styles(response):
    if request.path.startswith("/bingo/static/") and request.path.endswith((".js", ".css")):
        response.headers["Cache-Control"] = "no-store"
    return response


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    doc = get_db().collection("users").document(uid).get()
    if not doc.exists:
        return None
    return {"id": uid, **doc.to_dict()}


@bingo_pages_bp.route("/")
def index():
    user = get_current_user()
    boards = []
    if user:
        db = get_db()
        owned_docs = (
            db.collection("games")
            .where("owner_id", "==", user["id"])
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        boards_by_id = {d.id: {"id": d.id, **d.to_dict()} for d in owned_docs}

        pb_docs = (
            db.collection("player_boards")
            .where("player_id", "==", user["id"])
            .stream()
        )
        joined_game_ids = {pb.get("game_id") for pb in pb_docs} - set(boards_by_id)
        for game_id in joined_game_ids:
            game_doc = db.collection("games").document(game_id).get()
            if game_doc.exists:
                boards_by_id[game_id] = {"id": game_id, **game_doc.to_dict()}

        archived_ids = set(user.get("archived_game_ids") or [])
        boards = sorted(
            [b for b in boards_by_id.values() if b["id"] not in archived_ids],
            key=lambda b: b.get("created_at") or 0,
            reverse=True,
        )
    return render_template("bingo/index.html", user=user, boards=boards)


@bingo_pages_bp.route("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("bingo_pages.index"))
    return render_template("bingo/login.html")


@bingo_pages_bp.route("/manifest.webmanifest")
def manifest():
    def icon(name, sizes, purpose="any"):
        return {
            "src": url_for("bingo_pages.static", filename=f"icons/{name}"),
            "sizes": sizes,
            "type": "image/png",
            "purpose": purpose,
        }

    resp = jsonify({
        "name": "Social Bingo",
        "short_name": "Bingo",
        "description": "Create and share custom bingo boards for parties, game nights, and any occasion.",
        "start_url": url_for("bingo_pages.index"),
        "scope": url_for("bingo_pages.index"),
        "display": "standalone",
        "background_color": "#f3e7d3",
        "theme_color": "#6b1f2a",
        "icons": [
            icon("icon-192.png", "192x192"),
            icon("icon-512.png", "512x512"),
            icon("icon-maskable-512.png", "512x512", purpose="maskable"),
        ],
    })
    resp.mimetype = "application/manifest+json"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bingo_pages_bp.route("/sw.js")
def service_worker():
    # Installability-only service worker: a fetch handler must exist for
    # Chrome/Android to treat the site as an installable PWA, but it does
    # no caching so it can't ever serve stale content during active dev.
    # no-store so the browser can't sit on a stale copy of the script itself.
    resp = Response(
        "self.addEventListener('fetch', () => {});\n",
        mimetype="application/javascript",
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bingo_pages_bp.route("/boards/create")
@login_required
def create_board():
    user = get_current_user()
    return render_template("bingo/boards/create.html", user=user)


@bingo_pages_bp.route("/boards/<board_id>")
@login_required
def view_board(board_id):
    user = get_current_user()
    db = get_db()

    game_doc = db.collection("games").document(board_id).get()
    if not game_doc.exists:
        abort(404)
    game = {"id": game_doc.id, **game_doc.to_dict()}

    pb_docs = (
        db.collection("player_boards")
        .where("player_id", "==", user["id"])
        .where("game_id", "==", board_id)
        .limit(1)
        .get()
    )

    if not pb_docs:
        if game["owner_id"] != user["id"]:
            abort(404)
        tile_ids = build_player_tile_ids(game["tile_pool"], game["board_size"])
        _, pb_ref = db.collection("player_boards").add({
            "player_id": user["id"],
            "game_id": board_id,
            "tile_ids": tile_ids,
            "created_at": datetime.now(timezone.utc),
        })
        pb_doc = db.collection("player_boards").document(pb_ref.id).get()
    else:
        pb_doc = pb_docs[0]

    size = game["board_size"]
    pool_by_id = tile_pool_by_id(game["tile_pool"])
    tiles = [
        with_photo_urls(board_id, t)
        for t in resolve_board_tiles(pool_by_id, pb_doc.get("tile_ids"))
    ]
    player_board = {
        "id": pb_doc.id,
        "tiles": reshape_2d(tiles, size),
        "has_bingo": check_bingo(tiles, size),
    }

    return render_template("bingo/boards/view.html", user=user, player_board=player_board, game=game)


@bingo_pages_bp.route("/photos/<game_id>/<filename>")
@login_required
def tile_photo(game_id, filename):
    user = get_current_user()
    db = get_db()

    game_doc = db.collection("games").document(game_id).get()
    if not game_doc.exists:
        abort(404)
    if not user_in_game(db, game_doc, user):
        abort(403)

    path = resolve_photo_path(game_id, filename)
    if not path or not path.is_file():
        abort(404)
    return send_file(path)


@bingo_pages_bp.route("/join")
@login_required
def join_board():
    code = request.args.get("code", "").strip().upper()
    if not code:
        return redirect(url_for("bingo_pages.index"))

    db = get_db()
    game_docs = db.collection("games").where("share_code", "==", code).limit(1).get()
    if not game_docs:
        abort(404)
    game_doc = game_docs[0]
    game = {"id": game_doc.id, **game_doc.to_dict()}

    user = get_current_user()
    existing = (
        db.collection("player_boards")
        .where("player_id", "==", user["id"])
        .where("game_id", "==", game["id"])
        .limit(1)
        .get()
    )
    if existing:
        archived = user.get("archived_game_ids") or []
        if game["id"] in archived:
            archived.remove(game["id"])
            db.collection("users").document(user["id"]).update({"archived_game_ids": archived})
        return redirect(url_for("bingo_pages.view_board", board_id=game["id"]))

    tile_ids = build_player_tile_ids(game["tile_pool"], game["board_size"])
    db.collection("player_boards").add({
        "player_id": user["id"],
        "game_id": game["id"],
        "tile_ids": tile_ids,
        "created_at": datetime.now(timezone.utc),
    })
    return redirect(url_for("bingo_pages.view_board", board_id=game["id"]))
