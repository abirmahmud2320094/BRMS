from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, DEMO_USERS, get_current_user
from app.core.config import get_settings
from app.models.schemas import DemoLogin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return user.__dict__


@router.post("/demo-login")
def demo_login(payload: DemoLogin):
    if get_settings().auth_mode.lower() != "demo":
        raise HTTPException(status_code=404, detail="Demo login is disabled")
    record = DEMO_USERS.get(payload.email.lower())
    if not record or payload.password != record["password"]:
        raise HTTPException(status_code=401, detail="Invalid demo credentials")
    return {
        "token": f"demo:{record['uid']}",
        "user": {"uid": record["uid"], "email": payload.email, "name": record["name"], "role": record["role"], "status": "active"},
    }
