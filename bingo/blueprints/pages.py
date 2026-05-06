from datetime import datetime, timezone
from flask import Blueprint, render_template, session, redirect, url_for, request, abort
from ..extensions import get_db
from ..decorators import login_required
from ..services.bingo_service import build_player_layout, empty_completion_state

bingo_pages_bp = Blueprint(
    "bingo_pages", __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/static",
)


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
        docs = (
            get_db()
            .collection("games")
            .where("owner_id", "==", user["id"])
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        boards = [{"id": d.id, **d.to_dict()} for d in docs]
    return render_template("bingo/index.html", user=user, boards=boards)


@bingo_pages_bp.route("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("bingo_pages.index"))
    return render_template("bingo/login.html")


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

    pb_docs = (
        db.collection("player_boards")
        .where("player_id", "==", user["id"])
        .where("game_id", "==", board_id)
        .limit(1)
        .get()
    )
    if not pb_docs:
        abort(404)
    pb_doc = pb_docs[0]
    player_board = {"id": pb_doc.id, **pb_doc.to_dict()}

    game_doc = db.collection("games").document(board_id).get()
    if not game_doc.exists:
        abort(404)
    game = {"id": game_doc.id, **game_doc.to_dict()}

    return render_template("bingo/boards/view.html", user=user, player_board=player_board, game=game)


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
        return redirect(url_for("bingo_pages.view_board", board_id=game["id"]))

    layout = build_player_layout(game["tile_pool"], game["board_size"])
    state = empty_completion_state(game["board_size"])
    db.collection("player_boards").add({
        "player_id": user["id"],
        "game_id": game["id"],
        "tile_layout": layout,
        "completion_state": state,
        "has_bingo": False,
        "created_at": datetime.now(timezone.utc),
    })
    return redirect(url_for("bingo_pages.view_board", board_id=game["id"]))
