def init_games(app):
    from .blueprints.pages import games_pages_bp

    app.register_blueprint(games_pages_bp, url_prefix="/games")
