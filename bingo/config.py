import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class BingoConfig:
    SECRET_KEY = os.environ["SECRET_KEY"]
    FIREBASE_CREDENTIALS_PATH = os.environ["FIREBASE_CREDENTIALS_PATH"]

    GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
    GOOGLE_REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]

    ODDS_ADMIN_USERNAME = os.environ["ODDS_ADMIN_USERNAME"]
    ODDS_ADMIN_PASSWORD = os.environ["ODDS_ADMIN_PASSWORD"]

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # only takes effect for sessions explicitly marked session.permanent = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=180)
