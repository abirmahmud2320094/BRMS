from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_roles
from app.core.config import get_settings
from app.core.firebase import firebase_auth_client
from app.models.schemas import UserCreate, UserUpdate
from app.services.store import get_store

router = APIRouter(prefix="/users", tags=["User Administration"])


@router.get("")
def list_users(user=Depends(require_roles("administrator"))):
    return get_store().list("users")


@router.post("")
def create_user(payload: UserCreate, user=Depends(require_roles("administrator"))):
    settings = get_settings()
    if settings.auth_mode.lower() == "demo":
        raise HTTPException(status_code=400, detail="Create real users in Firebase mode. Demo accounts are fixed for presentation.")
    try:
        auth_client = firebase_auth_client()
        firebase_user = auth_client.create_user(email=payload.email, password=payload.password, display_name=payload.name)
        profile = payload.model_dump(exclude={"password"}, mode="json")
        return get_store().create("users", profile, doc_id=firebase_user.uid)
    except Exception as exc:
        if exc.__class__.__name__ == "EmailAlreadyExistsError":
            raise HTTPException(status_code=409, detail="A Firebase account already exists for this email address.") from exc
        raise HTTPException(status_code=400, detail="Unable to create the Firebase user. Check the account details and try again.") from exc


@router.patch("/{uid}")
def update_user(uid: str, payload: UserUpdate, user=Depends(require_roles("administrator"))):
    current = get_store().get("users", uid)
    if not current:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_none=True, mode="json")
    if not data:
        raise HTTPException(status_code=400, detail="No changes supplied")
    return get_store().update("users", uid, data)


@router.delete("/{uid}")
def delete_user(uid: str, user=Depends(require_roles("administrator"))):
    if uid == user.uid:
        raise HTTPException(status_code=409, detail="You cannot delete your own active administrator account.")

    store = get_store()
    target = store.get("users", uid)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.get("role") == "administrator" and target.get("status", "active") == "active":
        other_active_admins = [
            profile
            for profile in store.find("users", role="administrator", status="active")
            if profile["id"] != uid
        ]
        if not other_active_admins:
            raise HTTPException(status_code=409, detail="The last active administrator cannot be deleted.")

    if get_settings().auth_mode.lower() == "demo":
        raise HTTPException(status_code=409, detail="User deletion is unavailable in the current authentication environment.")

    auth_client = firebase_auth_client()
    auth_disabled = False
    try:
        auth_client.update_user(uid, disabled=True)
        auth_disabled = True
    except Exception as exc:
        if exc.__class__.__name__ != "UserNotFoundError":
            raise HTTPException(status_code=500, detail="Unable to safely disable the authentication account.") from exc

    try:
        if not store.delete("users", uid):
            raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        if auth_disabled:
            try:
                auth_client.update_user(uid, disabled=False)
            except Exception:
                pass
        raise

    return {"deleted": True, "authentication_account": "disabled"}
