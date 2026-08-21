from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import auth as auth_module
from app.services.store import StoreUnavailable


class ProfileStore:
    def __init__(self, profiles):
        self.profiles = profiles
        self.requested_ids = []

    def get(self, collection, doc_id):
        assert collection == "users"
        self.requested_ids.append(doc_id)
        return self.profiles.get(doc_id)


@pytest.mark.parametrize(
    ("uid", "role"),
    [
        ("manager-firebase-uid", "building_manager"),
        ("accountant-firebase-uid", "accountant"),
    ],
)
def test_firebase_uid_loads_matching_firestore_profile(monkeypatch, uid, role):
    store = ProfileStore(
        {
            uid: {
                "name": "Authorized User",
                "email": "user@example.com",
                "role": role,
                "status": "active",
            }
        }
    )
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(auth_mode="firebase"),
    )
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda token: {"uid": uid, "email": "user@example.com"},
    )
    monkeypatch.setattr(auth_module, "get_store", lambda: store)

    user = auth_module.get_current_user("Bearer verified-firebase-token")

    assert store.requested_ids == [uid]
    assert user.uid == uid
    assert user.role == role


def test_missing_firestore_profile_returns_403(monkeypatch):
    monkeypatch.setattr(auth_module, "get_store", lambda: ProfileStore({}))

    with pytest.raises(HTTPException) as exc_info:
        auth_module._load_profile("firebase-uid", "user@example.com")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "No BRMS user profile is assigned to this account"


def test_firestore_outage_remains_store_unavailable(monkeypatch):
    class UnavailableStore:
        def get(self, collection, doc_id):
            raise StoreUnavailable("sanitized storage failure")

    monkeypatch.setattr(auth_module, "get_store", lambda: UnavailableStore())

    with pytest.raises(StoreUnavailable, match="sanitized storage failure"):
        auth_module._load_profile("firebase-uid", "user@example.com")
