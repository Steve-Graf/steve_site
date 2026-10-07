from bingo.extensions import init_firebase


def init_odds(app):
    init_firebase(app.config["FIREBASE_CREDENTIALS_PATH"])

    from .odds_routes import odds_bp
    from .auth_routes import odds_auth_bp
    from .pwa_routes import odds_pwa_bp
    from .survivor_routes import odds_survivor_bp
    from .admin_routes import odds_admin_bp

    app.register_blueprint(odds_bp)
    app.register_blueprint(odds_auth_bp)
    app.register_blueprint(odds_pwa_bp)
    app.register_blueprint(odds_survivor_bp)
    app.register_blueprint(odds_admin_bp)
