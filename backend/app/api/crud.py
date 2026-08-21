from typing import Optional, Type
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import require_roles, get_current_user
from app.services.store import get_store


def make_crud_router(
    *,
    prefix: str,
    collection: str,
    model: Type[BaseModel],
    write_roles=("administrator", "building_manager"),
    read_roles=("administrator", "building_manager", "accountant"),
    before_create=None,
    before_update=None,
    before_delete=None,
    unique_fields=(),
    duplicate_detail="Duplicate record",
):
    router = APIRouter(prefix=prefix, tags=[prefix.strip("/").replace("-", " ").title()])

    @router.get("")
    def list_records(search: Optional[str] = Query(default=None), user=Depends(require_roles(*read_roles))):
        records = get_store().list(collection)
        if search:
            s = search.lower()
            records = [r for r in records if s in str(r).lower()]
        return records

    @router.get("/{doc_id}")
    def get_record(doc_id: str, user=Depends(require_roles(*read_roles))):
        item = get_store().get(collection, doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Record not found")
        return item

    @router.post("")
    def create_record(payload: model, user=Depends(require_roles(*write_roles))):
        data = payload.model_dump(mode="json")
        if before_create:
            data = before_create(data, user) or data
        data["created_by"] = user.uid
        if unique_fields:
            unique_filters = {field: data[field] for field in unique_fields}
            return get_store().create_unique(collection, data, unique_filters, duplicate_detail)
        return get_store().create(collection, data)

    @router.patch("/{doc_id}")
    def update_record(doc_id: str, payload: dict, user=Depends(require_roles(*write_roles))):
        if not get_store().get(collection, doc_id):
            raise HTTPException(status_code=404, detail="Record not found")
        allowed_fields = set(model.model_fields.keys())
        data = {k: v for k, v in payload.items() if k in allowed_fields}
        if not data:
            raise HTTPException(status_code=400, detail="No valid fields supplied")
        validated = model(**{**{k: v for k, v in get_store().get(collection, doc_id).items() if k in allowed_fields}, **data}).model_dump(mode="json")
        if before_update:
            validated = before_update(doc_id, validated, user) or validated
        validated["updated_by"] = user.uid
        if unique_fields:
            unique_filters = {field: validated[field] for field in unique_fields}
            return get_store().update_unique(collection, doc_id, validated, unique_filters, duplicate_detail)
        return get_store().update(collection, doc_id, validated)

    @router.delete("/{doc_id}")
    def delete_record(doc_id: str, user=Depends(require_roles(*write_roles))):
        if before_delete:
            before_delete(doc_id, user)
        if not get_store().delete(collection, doc_id):
            raise HTTPException(status_code=404, detail="Record not found")
        return {"deleted": True}

    return router
