def init_golf(app):
    from .blueprints.pages import golf_pages_bp
    app.register_blueprint(golf_pages_bp, url_prefix="/golf")
