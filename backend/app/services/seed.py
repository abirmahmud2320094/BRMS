from app.core.auth import DEMO_USERS
from app.services.store import COLLECTIONS, get_store


def _ensure_demo_users(store):
    for email, item in DEMO_USERS.items():
        profile = {
            "name": item["name"],
            "email": email,
            "role": item["role"],
            "status": "active",
        }
        if store.get("users", item["uid"]):
            store.update("users", item["uid"], profile)
        else:
            store.create("users", profile, doc_id=item["uid"])


def seed_demo_data(force: bool = False):
    """Seed deterministic, linked presentation data in the configured store."""
    store = get_store()
    store.health_check()

    if force:
        for collection in reversed(COLLECTIONS):
            for item in store.list(collection):
                store.delete(collection, item["id"])

    _ensure_demo_users(store)
    if store.list("buildings"):
        return {"seeded": False, "reason": "business data already exists", "users_ensured": 3}

    building = store.create(
        "buildings",
        {
            "name": "IUB Commerce Centre",
            "address": "Bashundhara R/A, Dhaka",
            "city": "Dhaka",
            "contact_phone": "+880 1700-000000",
            "total_area": 42000,
            "notes": "Presentation building profile for the BRMS academic project.",
        },
        doc_id="demo-building",
    )

    floor_defs = [(0, "Ground Floor"), (1, "First Floor"), (2, "Second Floor"), (3, "Third Floor")]
    floors = []
    for level, name in floor_defs:
        floors.append(
            store.create(
                "floors",
                {
                    "building_id": building["id"],
                    "name": name,
                    "level": level,
                    "description": f"Commercial units on {name}.",
                },
                doc_id=f"demo-floor-{level}",
            )
        )

    shop_names = [
        "Nova Tech",
        "Urban Threads",
        "Cafe Nine",
        "Pixel Point",
        "Book Haven",
        "Glow Studio",
        "SmartFix",
        "Green Basket",
        "Arcade Hub",
        "Craft Corner",
        "Metro Pharmacy",
        "Prime Optics",
    ]
    shops = []
    for index, name in enumerate(shop_names):
        floor = floors[index // 3]
        shops.append(
            store.create(
                "shops",
                {
                    "floor_id": floor["id"],
                    "shop_number": f"{floor['level']}{index % 3 + 1:02d}",
                    "name": name,
                    "monthly_rent": 28000 + (index * 1800),
                    "area_sqft": 450 + (index % 3) * 70,
                    "status": "available",
                    "notes": "",
                },
                doc_id=f"demo-shop-{index + 1:02d}",
            )
        )

    tenant_defs = [
        ("Tahmid Hasan", "Nova Tech Solutions", "+8801711111111", "tahmid@example.com"),
        ("Maliha Islam", "Urban Threads", "+8801722222222", "maliha@example.com"),
        ("Farhan Kabir", "Cafe Nine", "+8801733333333", "farhan@example.com"),
        ("Nusrat Jahan", "Pixel Point", "+8801744444444", "nusrat@example.com"),
        ("Samiul Karim", "Book Haven", "+8801755555555", "samiul@example.com"),
        ("Rafia Noor", "Glow Studio", "+8801766666666", "rafia@example.com"),
        ("Adnan Chowdhury", "SmartFix", "+8801777777777", "adnan@example.com"),
    ]
    tenants = []
    for index, (name, business_name, phone, email) in enumerate(tenant_defs):
        tenants.append(
            store.create(
                "tenants",
                {
                    "name": name,
                    "business_name": business_name,
                    "phone": phone,
                    "email": email,
                    "national_id": None,
                    "address": "Dhaka, Bangladesh",
                    "status": "active",
                },
                doc_id=f"demo-tenant-{index + 1:02d}",
            )
        )

    tenancies = []
    for index, tenant in enumerate(tenants):
        shop = shops[index]
        tenancies.append(
            store.create_tenancy(
                {
                    "tenant_id": tenant["id"],
                    "shop_id": shop["id"],
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "monthly_rent": shop["monthly_rent"],
                    "security_deposit": shop["monthly_rent"] * 2,
                    "status": "active",
                    "notes": "",
                },
                doc_id=f"demo-tenancy-{index + 1:02d}",
            )
        )

    for month in ["2026-05", "2026-06", "2026-07", "2026-08"]:
        for index, tenancy in enumerate(tenancies):
            paid = not (month == "2026-08" and index in (2, 5))
            store.create(
                "rent_payments",
                {
                    "tenancy_id": tenancy["id"],
                    "accounting_month": month,
                    "amount": tenancy["monthly_rent"] if paid else 0,
                    "payment_date": f"{month}-05" if paid else None,
                    "status": "paid" if paid else "unpaid",
                    "reference": f"RCPT-{month.replace('-', '')}-{index + 1:03d}" if paid else None,
                    "note": "",
                },
                doc_id=f"demo-rent-{index + 1:02d}-{month.replace('-', '')}",
            )

    utility_types = ["electricity", "water", "service_charge"]
    for index, tenancy in enumerate(tenancies):
        for utility_index, utility_type in enumerate(utility_types):
            amount = 1100 + index * 120 + utility_index * 350
            store.create(
                "utility_bills",
                {
                    "shop_id": tenancy["shop_id"],
                    "tenancy_id": tenancy["id"],
                    "utility_type": utility_type,
                    "accounting_month": "2026-08",
                    "amount": amount,
                    "due_date": "2026-08-25",
                    "status": "paid" if index % 3 != 0 else "unpaid",
                    "note": "",
                },
                doc_id=f"demo-utility-{index + 1:02d}-{utility_type}-202608",
            )

    maintenance = [
        ("2026-08-02", "Generator preventive servicing and oil replacement", 12500, "completed"),
        ("2026-08-08", "Ground floor corridor lighting replacement", 6800, "completed"),
        ("2026-08-14", "Elevator control panel inspection", 9500, "completed"),
        ("2026-08-21", "Roof drainage line cleaning", 4200, "planned"),
    ]
    for index, (maintenance_date, description, cost, status) in enumerate(maintenance):
        store.create(
            "maintenance_records",
            {
                "scope_type": "building",
                "scope_id": building["id"],
                "maintenance_date": maintenance_date,
                "description": description,
                "cost": cost,
                "status": status,
                "notes": "",
            },
            doc_id=f"demo-maintenance-{index + 1:02d}",
        )

    return {
        "seeded": True,
        "building_id": building["id"],
        "counts": {
            "users": 3,
            "buildings": 1,
            "floors": len(floors),
            "shops": len(shops),
            "tenants": len(tenants),
            "tenancies": len(tenancies),
            "rent_payments": len(tenancies) * 4,
            "utility_bills": len(tenancies) * len(utility_types),
            "maintenance_records": len(maintenance),
        },
    }
