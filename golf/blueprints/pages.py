from flask import Blueprint, render_template

golf_pages_bp = Blueprint(
    "golf_pages", __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/static",
)


@golf_pages_bp.route("/")
def index():
    return render_template("golf/index.html")
