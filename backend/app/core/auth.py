from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.core.firebase import verify_firebase_token
from app.services.store import get_store


@dataclass
class CurrentUser:
    uid: str
    email: str
    name: str
    role: str
    status: str = "active"


DEMO_USERS = {
    "admin@brms.demo": {
        "uid": "demo-admin",
        "name": "Ayesha Rahman",
        "role": "administrator",
        "password": "Demo123!",
    },
    "manager@brms.demo": {
        "uid": "demo-manager",
        "name": "Nafis Ahmed",
        "role": "building_manager",
        "password": "Demo123!",
    },
    "accountant@brms.demo": {
        "uid": "demo-accountant",
        "name": "Samira Khan",
        "role": "accountant",
        "password": "Demo123!",
    },
}


def _load_profile(uid: str, email: str) -> CurrentUser:
    profile = get_store().get("users", uid)

    if not profile:
        raise HTTPException(
            status_code=403,
            detail="No BRMS user profile is assigned to this account",
        )

    if profile.get("status", "active") != "active":
        raise HTTPException(
            status_code=403,
            detail="This BRMS account is inactive",
        )

    return CurrentUser(
        uid=uid,
        email=email,
        name=profile.get("name", email),
        role=profile.get("role", "accountant"),
        status=profile.get("status", "active"),
    )


def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> CurrentUser:
    settings = get_settings()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = authorization.split(" ", 1)[1].strip()

    # Demo authentication mode
    if settings.auth_mode.lower() == "demo":
        if not token.startswith("demo:"):
            raise HTTPException(
                status_code=401,
                detail="Invalid demo token",
            )

        uid = token.split(":", 1)[1]

        match = next(
            (
                v | {"email": k}
                for k, v in DEMO_USERS.items()
                if v["uid"] == uid
            ),
            None,
        )

        if not match:
            raise HTTPException(
                status_code=401,
                detail="Invalid demo user",
            )

        profile = get_store().get("users", uid)

        if profile:
            return _load_profile(uid, match["email"])

        return CurrentUser(
            uid=uid,
            email=match["email"],
            name=match["name"],
            role=match["role"],
        )

    # Firebase authentication mode
    try:
        decoded = verify_firebase_token(token)

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Firebase token",
        )

    return _load_profile(
        decoded["uid"],
        decoded.get("email", ""),
    )


def require_roles(*roles: str) -> Callable:
    def dep(
        user: CurrentUser = Depends(get_current_user),
    ):
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action",
            )

        return user

    return dep