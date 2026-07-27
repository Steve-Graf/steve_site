def init_tts(app):
    from .blueprints.pages import tts_pages_bp
    app.register_blueprint(tts_pages_bp, url_prefix="/tts")
