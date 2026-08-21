from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.auth import require_roles
from app.services.store import get_store

router = APIRouter(tags=["Dashboard & Reports"])


def _month(value: Optional[str]):
    return value or datetime.now(timezone.utc).strftime("%Y-%m")


@router.get("/dashboard")
def dashboard(user=Depends(require_roles("administrator","building_manager","accountant"))):
    store = get_store()
    shops = store.list("shops")
    tenants = store.list("tenants")
    floors = store.list("floors")
    current_month = _month(None)
    rents = [r for r in store.list("rent_payments") if r.get("accounting_month") == current_month]
    utilities = [u for u in store.list("utility_bills") if u.get("accounting_month") == current_month]
    maint = store.list("maintenance_records")
    active_tenancies = store.find("tenancies", status="active")

    rent_expected = sum(float(t.get("monthly_rent", 0)) for t in active_tenancies)
    rent_collected = sum(float(r.get("amount", 0)) for r in rents if r.get("status") in ("paid","partial"))
    utility_due = sum(float(u.get("amount", 0)) for u in utilities if u.get("status") != "paid")
    month_maintenance = sum(float(m.get("cost", 0)) for m in maint if str(m.get("maintenance_date", "")).startswith(current_month))

    recent = []
    for collection, label in [("rent_payments","Rent payment"),("utility_bills","Utility bill"),("maintenance_records","Maintenance")]:
        for item in store.list(collection)[-4:]:
            recent.append({"type": label, "id": item["id"], "created_at": item.get("created_at"), "status": item.get("status"), "amount": item.get("amount", item.get("cost"))})
    recent = sorted(recent, key=lambda x: str(x.get("created_at") or ""), reverse=True)[:6]

    return {
        "month": current_month,
        "metrics": {
            "floors": len(floors),
            "shops": len(shops),
            "occupied_shops": sum(1 for s in shops if s.get("status") == "occupied"),
            "available_shops": sum(1 for s in shops if s.get("status") == "available"),
            "active_tenants": sum(1 for t in tenants if t.get("status") == "active"),
            "rent_expected": rent_expected,
            "rent_collected": rent_collected,
            "utility_due": utility_due,
            "maintenance_cost": month_maintenance,
        },
        "recent_activity": recent,
    }


@router.get("/reports/monthly")
def monthly_report(month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user=Depends(require_roles("administrator","building_manager","accountant"))):
    store = get_store()
    rents = [r for r in store.list("rent_payments") if r.get("accounting_month") == month]
    utilities = [u for u in store.list("utility_bills") if u.get("accounting_month") == month]
    maint = [m for m in store.list("maintenance_records") if str(m.get("maintenance_date", "")).startswith(month)]
    tenancies = {t["id"]: t for t in store.list("tenancies")}
    shops = {s["id"]: s for s in store.list("shops")}
    tenants = {t["id"]: t for t in store.list("tenants")}

    rent_rows = []
    for r in rents:
        tenancy = tenancies.get(r.get("tenancy_id"), {})
        shop = shops.get(tenancy.get("shop_id"), {})
        tenant = tenants.get(tenancy.get("tenant_id"), {})
        rent_rows.append({**r, "shop_number": shop.get("shop_number"), "tenant_name": tenant.get("business_name") or tenant.get("name")})

    expected = sum(float(t.get("monthly_rent", 0)) for t in tenancies.values() if t.get("status") == "active")
    collected = sum(float(r.get("amount", 0)) for r in rents if r.get("status") in ("paid","partial"))
    utility_total = sum(float(u.get("amount", 0)) for u in utilities)
    utility_outstanding = sum(float(u.get("amount", 0)) for u in utilities if u.get("status") != "paid")
    maintenance_total = sum(float(m.get("cost", 0)) for m in maint)

    return {
        "month": month,
        "summary": {
            "rent_expected": expected,
            "rent_collected": collected,
            "rent_outstanding": max(expected - collected, 0),
            "utility_total": utility_total,
            "utility_outstanding": utility_outstanding,
            "maintenance_total": maintenance_total,
        },
        "rent_rows": rent_rows,
        "utility_rows": utilities,
        "maintenance_rows": maint,
    }
