from fastapi.testclient import TestClient


def test_complete_demo_storage_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "demo")
    monkeypatch.setenv("DATA_MODE", "local")
    monkeypatch.setenv("LOCAL_DATA_PATH", str(tmp_path / "workflow.json"))

    from app.core.config import get_settings
    from app.services.store import reset_store

    get_settings.cache_clear()
    reset_store()

    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/demo-login", json={"email": "admin@brms.demo", "password": "Demo123!"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        health = client.get("/api/v1/system/health")
        assert health.json()["auth_mode"] == "demo"
        assert health.json()["data_mode"] == "local"
        assert client.get("/api/v1/dashboard", headers=headers).status_code == 200

        building = client.get("/api/v1/buildings", headers=headers).json()[0]
        assert client.patch(f"/api/v1/buildings/{building['id']}", headers=headers, json={"notes": "Workflow verified"}).status_code == 200

        floor = client.post(
            "/api/v1/floors",
            headers=headers,
            json={"building_id": building["id"], "name": "Workflow Floor", "level": 10, "description": "Integration test"},
        )
        assert floor.status_code == 200
        shop = client.post(
            "/api/v1/shops",
            headers=headers,
            json={"floor_id": floor.json()["id"], "shop_number": "WF-01", "name": "Workflow Shop", "monthly_rent": 35000, "area_sqft": 500, "status": "available", "notes": ""},
        )
        assert shop.status_code == 200
        tenant = client.post(
            "/api/v1/tenants",
            headers=headers,
            json={"name": "Workflow Tenant", "business_name": "Workflow Ltd", "phone": "+8801700000000", "email": "workflow@example.com", "national_id": None, "address": "Dhaka", "status": "active"},
        )
        assert tenant.status_code == 200
        invalid_tenancy = client.post(
            "/api/v1/tenancies",
            headers=headers,
            json={"tenant_id": tenant.json()["id"], "shop_id": shop.json()["id"], "start_date": "2026-08-20", "end_date": "2026-08-06", "monthly_rent": 35000, "security_deposit": 70000, "status": "active", "notes": ""},
        )
        assert invalid_tenancy.status_code == 422
        assert "End date must be later than the start date" in invalid_tenancy.json()["detail"][0]["msg"]
        tenancy = client.post(
            "/api/v1/tenancies",
            headers=headers,
            json={"tenant_id": tenant.json()["id"], "shop_id": shop.json()["id"], "start_date": "2026-09-01", "end_date": None, "monthly_rent": 35000, "security_deposit": 70000, "status": "active", "notes": ""},
        )
        assert tenancy.status_code == 200
        assert client.get(f"/api/v1/shops/{shop.json()['id']}", headers=headers).json()["status"] == "occupied"

        rent_payload = {"tenancy_id": tenancy.json()["id"], "accounting_month": "2026-09", "amount": 35000, "payment_date": "2026-09-05", "status": "paid", "reference": "WF-RENT-001", "note": ""}
        rent = client.post("/api/v1/rent-payments", headers=headers, json=rent_payload)
        assert rent.status_code == 200
        duplicate_rent = client.post("/api/v1/rent-payments", headers=headers, json=rent_payload)
        assert duplicate_rent.status_code == 409

        utility = client.post(
            "/api/v1/utility-bills",
            headers=headers,
            json={"shop_id": shop.json()["id"], "tenancy_id": tenancy.json()["id"], "utility_type": "electricity", "accounting_month": "2026-09", "amount": 2200, "due_date": "2026-09-20", "status": "unpaid", "note": ""},
        )
        assert utility.status_code == 200
        maintenance = client.post(
            "/api/v1/maintenance",
            headers=headers,
            json={"scope_type": "shop", "scope_id": shop.json()["id"], "maintenance_date": "2026-09-10", "description": "Electrical inspection", "cost": 1500, "status": "completed", "notes": ""},
        )
        assert maintenance.status_code == 200
        assert client.get("/api/v1/reports/monthly?month=2026-09", headers=headers).status_code == 200

        ended = client.post(f"/api/v1/tenancies/{tenancy.json()['id']}/end", headers=headers)
        assert ended.status_code == 200
        assert ended.json()["status"] == "ended"
        assert client.get(f"/api/v1/shops/{shop.json()['id']}", headers=headers).json()["status"] == "available"
        rent_records = client.get("/api/v1/rent-payments", headers=headers).json()
        assert any(record["id"] == rent.json()["id"] for record in rent_records)

        closed_tenancy = client.post(
            "/api/v1/tenancies",
            headers=headers,
            json={"tenant_id": tenant.json()["id"], "shop_id": shop.json()["id"], "start_date": "2026-10-01", "end_date": "2026-10-31", "monthly_rent": 35000, "security_deposit": 0, "status": "ended", "notes": "Completed tenancy"},
        )
        assert closed_tenancy.status_code == 200
        assert closed_tenancy.json()["end_date"] == "2026-10-31"

    reset_store()
    get_settings.cache_clear()
