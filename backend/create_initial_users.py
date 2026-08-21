"""Provision the initial BRMS manager and accountant in Firebase Auth + Firestore.

Passwords are read only from environment variables and are never stored or printed.
Run this script from any directory; backend/.env is loaded automatically when present.
"""
import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=False)

from app.core.config import get_settings
from app.core.firebase import firebase_auth_client
from app.services.store import get_store


@dataclass(frozen=True)
class InitialUser:
    label: str
    email: str
    password: str
    name: str
    role: str


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable {name} is missing")
    return value


def load_initial_users() -> List[InitialUser]:
    users = [
        InitialUser(
            label="Manager",
            email=_required_environment("BRMS_MANAGER_EMAIL").lower(),
            password=_required_environment("BRMS_MANAGER_PASSWORD"),
            name="Building Manager",
            role="building_manager",
        ),
        InitialUser(
            label="Accountant",
            email=_required_environment("BRMS_ACCOUNTANT_EMAIL").lower(),
            password=_required_environment("BRMS_ACCOUNTANT_PASSWORD"),
            name="Accountant",
            role="accountant",
        ),
    ]
    for user in users:
        if "@" not in user.email:
            raise ValueError(f"{user.label} email is invalid")
        if len(user.password) < 6:
            raise ValueError(f"{user.label} password must contain at least 6 characters")
    if users[0].email == users[1].email:
        raise ValueError("Manager and Accountant emails must be different")
    return users


def provision_user(user: InitialUser, auth_client, store, update_existing_password: bool = False) -> Dict[str, str]:
    try:
        firebase_user = auth_client.get_user_by_email(user.email)
        auth_action = "reused"
        update_fields = {"display_name": user.name, "disabled": False}
        if update_existing_password:
            update_fields["password"] = user.password
        firebase_user = auth_client.update_user(firebase_user.uid, **update_fields)
    except auth_client.UserNotFoundError:
        firebase_user = auth_client.create_user(
            email=user.email,
            password=user.password,
            display_name=user.name,
            disabled=False,
        )
        auth_action = "created"

    profile = {
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": "active",
    }
    if store.get("users", firebase_user.uid):
        store.update("users", firebase_user.uid, profile)
        profile_action = "updated"
    else:
        store.create("users", profile, doc_id=firebase_user.uid)
        profile_action = "created"

    return {
        "label": user.label,
        "uid": firebase_user.uid,
        "email": user.email,
        "role": user.role,
        "auth_action": auth_action,
        "profile_action": profile_action,
    }


def _firebase_password_sign_in(email: str, password: str, web_api_key: str) -> str:
    import httpx

    endpoint = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    try:
        response = httpx.post(
            endpoint,
            params={"key": web_api_key},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=30,
        )
    except Exception as exc:
        raise RuntimeError("Firebase password authentication request failed") from exc
    if response.status_code != 200:
        raise RuntimeError("Firebase rejected the supplied temporary credentials")
    token = response.json().get("idToken")
    if not token:
        raise RuntimeError("Firebase authentication did not return an ID token")
    return token


def verify_api_access(users: List[InitialUser], results: List[Dict[str, str]], web_api_key: str):
    from fastapi.testclient import TestClient

    settings = get_settings()
    if settings.auth_mode != "firebase" or settings.data_mode != "firebase":
        raise RuntimeError("Verification requires AUTH_MODE=firebase and DATA_MODE=firebase")

    from app.main import app

    expected_by_email = {result["email"]: result for result in results}
    prefix = settings.api_v1_prefix
    with TestClient(app) as client:
        for user in users:
            token = _firebase_password_sign_in(user.email, user.password, web_api_key)
            headers = {"Authorization": f"Bearer {token}"}
            me_response = client.get(f"{prefix}/auth/me", headers=headers)
            if me_response.status_code != 200:
                raise RuntimeError(f"{user.label} /auth/me verification failed")
            profile = me_response.json()
            expected = expected_by_email[user.email]
            if profile.get("uid") != expected["uid"] or profile.get("role") != user.role or profile.get("status") != "active":
                raise RuntimeError(f"{user.label} profile or role verification failed")
            admin_response = client.get(f"{prefix}/users", headers=headers)
            if admin_response.status_code != 403:
                raise RuntimeError(f"{user.label} unexpectedly accessed an administrator-only endpoint")
            print(f"{user.label}: authentication OK; /auth/me role={user.role}; administrator endpoint=403")


def main():
    parser = argparse.ArgumentParser(description="Create or repair initial BRMS Firebase users and Firestore profiles.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Authenticate both users and verify /auth/me plus administrator-only access.",
    )
    parser.add_argument(
        "--update-existing-passwords",
        action="store_true",
        help="Replace passwords for existing Manager/Accountant users with the supplied environment values.",
    )
    args = parser.parse_args()

    try:
        settings = get_settings()
        if settings.data_mode != "firebase":
            raise ValueError("DATA_MODE=firebase is required")
        users = load_initial_users()
        web_api_key = _required_environment("FIREBASE_WEB_API_KEY") if args.verify else ""
        auth_client = firebase_auth_client()
        store = get_store()
        store.health_check()
        results = [
            provision_user(user, auth_client, store, update_existing_password=args.update_existing_passwords)
            for user in users
        ]
        for result in results:
            print(
                f"{result['label']}: Firebase Auth {result['auth_action']}; UID={result['uid']}; "
                f"Firestore profile {result['profile_action']}; role={result['role']}"
            )
        if args.verify:
            verify_api_access(users, results, web_api_key)
        else:
            print("Live password/API verification skipped. Re-run with --verify and FIREBASE_WEB_API_KEY.")
    except Exception as exc:
        raise SystemExit(f"Initial-user setup failed: {exc}")


if __name__ == "__main__":
    main()
