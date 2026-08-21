from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.services.store import get_store


def require_exists(collection: str, doc_id: str, label: Optional[str] = None):
    item = get_store().get(collection, doc_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{label or collection.rstrip('s').title()} not found")
    return item


def prevent_duplicate(collection: str, detail: str, **filters):
    if get_store().find(collection, **filters):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def ensure_shop_assignable(shop_id: str, ignore_tenancy_id: Optional[str] = None):
    shop = require_exists("shops", shop_id, "Shop")
    if shop.get("status") == "inactive":
        raise HTTPException(status_code=409, detail="Inactive shop cannot receive a tenant assignment")
    active = get_store().find("tenancies", shop_id=shop_id, status="active")
    active = [x for x in active if x.get("id") != ignore_tenancy_id]
    if active:
        raise HTTPException(status_code=409, detail="Shop already has an active tenant assignment")
    return shop


def end_tenancy(tenancy_id: str, end_date: Optional[str] = None):
    resolved_end_date = end_date or datetime.now(timezone.utc).date().isoformat()
    return get_store().end_tenancy(tenancy_id, resolved_end_date)
