import json
import os
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


@lru_cache
def get_firebase_app():
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as exc:
        raise RuntimeError("firebase-admin is required for Firebase mode. Run: pip install -r requirements.txt") from exc

    settings = get_settings()
    if firebase_admin._apps:
        return firebase_admin.get_app()

    options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
    if settings.firebase_service_account_json:
        try:
            service_account = json.loads(settings.firebase_service_account_json)
            cred = credentials.Certificate(service_account)
            return firebase_admin.initialize_app(cred, options=options)
        except (TypeError, ValueError, KeyError) as exc:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid service-account JSON") from exc

    if settings.google_application_credentials:
        credentials_path = Path(settings.google_application_credentials).expanduser()
        if not credentials_path.is_file():
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS does not point to a readable file")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path.resolve())

    try:
        return firebase_admin.initialize_app(options=options)
    except Exception as exc:
        raise RuntimeError(
            "Firebase Admin initialization failed. Configure GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON."
        ) from exc


def get_firestore_client():
    get_firebase_app()
    from firebase_admin import firestore
    return firestore.client()


def verify_firebase_token(token: str) -> dict:
    get_firebase_app()
    from firebase_admin import auth
    return auth.verify_id_token(token)


def firebase_auth_client():
    get_firebase_app()
    from firebase_admin import auth
    return auth
