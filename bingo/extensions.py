import firebase_admin
from firebase_admin import credentials, firestore
from authlib.integrations.flask_client import OAuth

oauth = OAuth()
_fs_client = None


def init_firebase(cred_path: str):
    global _fs_client
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    _fs_client = firestore.client()


def get_db():
    return _fs_client
