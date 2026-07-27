from flask import Blueprint, render_template

games_pages_bp = Blueprint(
    "games_pages", __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/static/games",
)

GAMES = [
    {
        "id": "purple",
        "icon": "🟣",
        "title": "Purple",
        "description": "Red, Black, or Purple??",
    },
    {
        "id": "bus",
        "icon": "🚌",
        "flip_icon": True,
        "title": "Ride the Bus",
        "description": "Can you get off the bus?",
    },
    {
        "id": "race",
        "icon": "🏇",
        "flip_icon": True,
        "title": "Horse Race",
        "description": "Race to the finish!",
    },
    {
        "id": "rocket",
        "icon": "🚀",
        "title": "Rocket",
        "description": "Bail before it explodes!",
    },
]


@games_pages_bp.route("/")
def index():
    return render_template("games/index.html", games=GAMES)


@games_pages_bp.route("/purple")
def purple():
    return render_template("games/purple.html")


@games_pages_bp.route("/bus")
def bus():
    return render_template("games/bus.html")


@games_pages_bp.route("/race")
def race():
    return render_template("games/race.html")


@games_pages_bp.route("/rocket")
def rocket():
    return render_template("games/rocket.html")
