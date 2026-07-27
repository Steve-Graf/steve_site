from flask import Blueprint, render_template

tts_pages_bp = Blueprint(
    "tts_pages", __name__,
    template_folder="../templates",
)

@tts_pages_bp.route("/")
def index():
    return render_template("tts/index.html")
