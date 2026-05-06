from .extensions import oauth, init_firebase


def init_bingo(app):
    init_firebase(app.config["FIREBASE_CREDENTIALS_PATH"])
    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from .blueprints.auth import auth_bp
    from .blueprints.pages import bingo_pages_bp
    from .blueprints.api import bingo_api_bp

    app.register_blueprint(auth_bp,        url_prefix="/bingo/auth")
    app.register_blueprint(bingo_pages_bp, url_prefix="/bingo")
    app.register_blueprint(bingo_api_bp,   url_prefix="/bingo/api")
