from fastapi import APIRouter, Depends, HTTPException

from app.api.crud import make_crud_router
from app.core.auth import require_roles
from app.models.schemas import BuildingBase, FloorBase, ShopBase, TenantBase, TenancyBase, RentPaymentBase, UtilityBillBase, MaintenanceBase
from app.services.business import require_exists, prevent_duplicate, ensure_shop_assignable, end_tenancy
from app.services.store import get_store

router = APIRouter()


def floor_before(data, user):
    require_exists("buildings", data["building_id"], "Building")
    prevent_duplicate("floors", "A floor with this level already exists", building_id=data["building_id"], level=data["level"])
    return data


def floor_update(doc_id, data, user):
    require_exists("buildings", data["building_id"], "Building")
    duplicates = [x for x in get_store().find("floors", building_id=data["building_id"], level=data["level"]) if x["id"] != doc_id]
    if duplicates:
        raise HTTPException(status_code=409, detail="A floor with this level already exists")
    return data


def floor_delete(doc_id, user):
    if get_store().find("shops", floor_id=doc_id):
        raise HTTPException(
            status_code=409,
            detail="This floor cannot be deleted because it contains shops. Delete or move the shops first.",
        )
    if get_store().find("maintenance_records", scope_type="floor", scope_id=doc_id):
        raise HTTPException(status_code=409, detail="This floor has maintenance history and cannot be deleted.")


def shop_before(data, user):
    require_exists("floors", data["floor_id"], "Floor")
    duplicates = get_store().find("shops", floor_id=data["floor_id"], shop_number=data["shop_number"])
    if duplicates:
        raise HTTPException(status_code=409, detail="Shop number already exists on this floor")
    return data


def shop_update(doc_id, data, user):
    require_exists("floors", data["floor_id"], "Floor")
    duplicates = [x for x in get_store().find("shops", floor_id=data["floor_id"], shop_number=data["shop_number"]) if x["id"] != doc_id]
    if duplicates:
        raise HTTPException(status_code=409, detail="Shop number already exists on this floor")
    active = get_store().find("tenancies", shop_id=doc_id, status="active")
    if active and data.get("status") == "available":
        data["status"] = "occupied"
    return data


def shop_delete(doc_id, user):
    if get_store().find("tenancies", shop_id=doc_id, status="active"):
        raise HTTPException(
            status_code=409,
            detail="This shop is currently occupied. End the active tenancy before deleting the shop.",
        )
    if get_store().find("tenancies", shop_id=doc_id) or get_store().find("utility_bills", shop_id=doc_id):
        raise HTTPException(status_code=409, detail="This shop has rental or billing history and cannot be deleted.")
    if get_store().find("maintenance_records", scope_type="shop", scope_id=doc_id):
        raise HTTPException(status_code=409, detail="This shop has maintenance history and cannot be deleted.")


def tenant_delete(doc_id, user):
    if get_store().find("tenancies", tenant_id=doc_id, status="active"):
        raise HTTPException(
            status_code=409,
            detail="This tenant has an active tenancy. End the tenancy before deleting the tenant.",
        )
    if get_store().find("tenancies", tenant_id=doc_id):
        raise HTTPException(status_code=409, detail="This tenant has rental history and cannot be deleted. Deactivate the tenant instead.")


def tenancy_before(data, user):
    require_exists("tenants", data["tenant_id"], "Tenant")
    ensure_shop_assignable(data["shop_id"])
    return data


def rent_before(data, user):
    require_exists("tenancies", data["tenancy_id"], "Tenancy")
    return data


def utility_before(data, user):
    require_exists("shops", data["shop_id"], "Shop")
    if data.get("tenancy_id"):
        require_exists("tenancies", data["tenancy_id"], "Tenancy")
    return data


def maintenance_before(data, user):
    if data.get("scope_id"):
        mapping = {"building":"buildings","floor":"floors","shop":"shops"}
        require_exists(mapping[data["scope_type"]], data["scope_id"], data["scope_type"].title())
    return data


def building_before(data, user):
    if get_store().list("buildings"):
        raise HTTPException(status_code=409, detail="BRMS Version 1 supports one building only. Update the existing profile instead.")
    return data

def building_delete(doc_id, user):
    if get_store().find("floors", building_id=doc_id):
        raise HTTPException(
            status_code=409,
            detail="This building cannot be deleted while it contains floors. Delete the related floors first.",
        )
    if get_store().find("maintenance_records", scope_type="building", scope_id=doc_id):
        raise HTTPException(status_code=409, detail="This building has maintenance history and cannot be deleted.")

router.include_router(make_crud_router(prefix="/buildings", collection="buildings", model=BuildingBase, before_create=building_before, before_delete=building_delete))
router.include_router(make_crud_router(prefix="/floors", collection="floors", model=FloorBase, before_create=floor_before, before_update=floor_update, before_delete=floor_delete, unique_fields=("building_id", "level"), duplicate_detail="A floor with this level already exists"))
router.include_router(make_crud_router(prefix="/shops", collection="shops", model=ShopBase, before_create=shop_before, before_update=shop_update, before_delete=shop_delete, unique_fields=("floor_id", "shop_number"), duplicate_detail="Shop number already exists on this floor"))
router.include_router(make_crud_router(prefix="/tenants", collection="tenants", model=TenantBase, before_delete=tenant_delete))
router.include_router(make_crud_router(prefix="/rent-payments", collection="rent_payments", model=RentPaymentBase, write_roles=("administrator","building_manager","accountant"), before_create=rent_before, unique_fields=("tenancy_id", "accounting_month"), duplicate_detail="A rent record already exists for this tenancy and month"))
router.include_router(make_crud_router(prefix="/utility-bills", collection="utility_bills", model=UtilityBillBase, write_roles=("administrator","building_manager","accountant"), before_create=utility_before, unique_fields=("shop_id", "utility_type", "accounting_month"), duplicate_detail="This utility bill already exists for the selected shop and month"))
router.include_router(make_crud_router(prefix="/maintenance", collection="maintenance_records", model=MaintenanceBase, before_create=maintenance_before))

# Tenancies need special side effects on shop occupancy.
tenancy_router = APIRouter(prefix="/tenancies", tags=["Tenancies"])

@tenancy_router.get("")
def list_tenancies(user=Depends(require_roles("administrator","building_manager","accountant"))):
    rows = get_store().list("tenancies")
    tenants = {x["id"]: x for x in get_store().list("tenants")}
    shops = {x["id"]: x for x in get_store().list("shops")}
    enriched = []
    for row in rows:
        tenant = tenants.get(row.get("tenant_id"), {})
        shop = shops.get(row.get("shop_id"), {})
        enriched.append({**row, "tenant_name": tenant.get("business_name") or tenant.get("name"), "shop_number": shop.get("shop_number"), "shop_name": shop.get("name")})
    return enriched

@tenancy_router.post("")
def create_tenancy(payload: TenancyBase, user=Depends(require_roles("administrator","building_manager"))):
    data = tenancy_before(payload.model_dump(mode="json"), user)
    data["created_by"] = user.uid
    return get_store().create_tenancy(data)

@tenancy_router.patch("/{doc_id}")
def update_tenancy(doc_id: str, payload: dict, user=Depends(require_roles("administrator","building_manager"))):
    current = require_exists("tenancies", doc_id, "Tenancy")
    merged = {k: v for k, v in current.items() if k in TenancyBase.model_fields}
    merged.update({k:v for k,v in payload.items() if k in TenancyBase.model_fields})
    validated = TenancyBase(**merged).model_dump(mode="json")
    return get_store().update_tenancy(doc_id, {**validated, "updated_by": user.uid})

@tenancy_router.post("/{doc_id}/end")
def finish_tenancy(doc_id: str, user=Depends(require_roles("administrator","building_manager"))):
    return end_tenancy(doc_id)

@tenancy_router.delete("/{doc_id}")
def delete_tenancy(doc_id: str, user=Depends(require_roles("administrator","building_manager"))):
    store = get_store()
    if not store.get("tenancies", doc_id):
        raise HTTPException(status_code=404, detail="Tenancy not found")
    if store.find("rent_payments", tenancy_id=doc_id) or store.find("utility_bills", tenancy_id=doc_id):
        raise HTTPException(
            status_code=409,
            detail="This tenancy has financial history and cannot be deleted. End the tenancy instead.",
        )
    if not store.delete_tenancy(doc_id):
        raise HTTPException(status_code=404, detail="Tenancy not found")
    return {"deleted": True}

router.include_router(tenancy_router)
