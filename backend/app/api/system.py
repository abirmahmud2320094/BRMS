from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_roles
from app.core.config import get_settings
from app.services.seed import seed_demo_data
from app.services.store import StoreError, get_store

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "auth_mode": settings.auth_mode,
        "data_mode": settings.data_mode,
        "storage_check": "lazy",
    }


@router.get("/readiness")
def readiness():
    settings = get_settings()
    try:
        get_store().health_check()
    except StoreError:
        raise HTTPException(
            status_code=503,
            detail="The configured data store is temporarily unavailable",
        )
    return {
        "status": "ready",
        "auth_mode": settings.auth_mode,
        "data_mode": settings.data_mode,
    }


@router.post("/seed-demo")
def seed(force: bool = False, user=Depends(require_roles("administrator"))):
    if get_settings().data_mode.lower() != "local":
        raise HTTPException(status_code=400, detail="Demo seed endpoint is available only in local data mode")
    return seed_demo_data(force=force)
