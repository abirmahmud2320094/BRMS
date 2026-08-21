import secrets
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.auth import me
from app.core.auth import CurrentUser, require_roles
from create_initial_users import InitialUser, provision_user


class FakeUserNotFoundError(Exception):
    pass


class FakeAuth:
    UserNotFoundError = FakeUserNotFoundError

    def __init__(self):
        self.users = {}
        self.created_passwords = []

    def get_user_by_email(self, email):
        if email not in self.users:
            raise self.UserNotFoundError()
        return self.users[email]

    def create_user(self, email, password, display_name, disabled):
        user = SimpleNamespace(uid=f"uid-{len(self.users) + 1}", email=email, display_name=display_name, disabled=disabled)
        self.users[email] = user
        self.created_passwords.append(password)
        return user

    def update_user(self, uid, **fields):
        user = next(item for item in self.users.values() if item.uid == uid)
        for key, value in fields.items():
            if key != "password":
                setattr(user, key, value)
        return user


class FakeStore:
    def __init__(self):
        self.profiles = {}

    def get(self, collection, uid):
        return self.profiles.get(uid)

    def create(self, collection, profile, doc_id):
        self.profiles[doc_id] = dict(profile)

    def update(self, collection, uid, profile):
        self.profiles[uid].update(profile)


def test_initial_user_provisioning_is_idempotent_and_never_stores_password():
    auth = FakeAuth()
    store = FakeStore()
    administrator = SimpleNamespace(uid="existing-admin", email="admin@brms.com", display_name="Administrator", disabled=False)
    auth.users[administrator.email] = administrator
    store.profiles[administrator.uid] = {"name": "Administrator", "email": administrator.email, "role": "administrator", "status": "active"}
    original_admin_profile = dict(store.profiles[administrator.uid])
    manager = InitialUser("Manager", "manager@brms.com", secrets.token_urlsafe(18), "Building Manager", "building_manager")
    accountant = InitialUser("Accountant", "accountant@brms.com", secrets.token_urlsafe(18), "Accountant", "accountant")

    first = [provision_user(user, auth, store) for user in (manager, accountant)]
    second = [provision_user(user, auth, store) for user in (manager, accountant)]

    assert [result["auth_action"] for result in first] == ["created", "created"]
    assert [result["auth_action"] for result in second] == ["reused", "reused"]
    assert len(auth.users) == 3
    assert store.profiles[first[0]["uid"]]["role"] == "building_manager"
    assert store.profiles[first[1]["uid"]]["role"] == "accountant"
    assert auth.users[administrator.email] is administrator
    assert store.profiles[administrator.uid] == original_admin_profile
    assert all("password" not in profile for profile in store.profiles.values())


@pytest.mark.parametrize("role", ["building_manager", "accountant"])
def test_initial_non_admin_roles_have_profile_access_but_not_admin_access(role):
    user = CurrentUser(uid=f"uid-{role}", email=f"{role}@brms.com", name=role, role=role)
    assert me(user)["role"] == role
    administrator_only = require_roles("administrator")
    with pytest.raises(HTTPException) as exc_info:
        administrator_only(user)
    assert exc_info.value.status_code == 403
