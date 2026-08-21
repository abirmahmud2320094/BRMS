from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def deletion_client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "demo")
    monkeypatch.setenv("DATA_MODE", "local")
    monkeypatch.setenv("LOCAL_DATA_PATH", str(tmp_path / "deletions.json"))

    from app.core.config import get_settings
    from app.services.store import reset_store

    get_settings.cache_clear()
    reset_store()

    import app.main as main_module

    main_module.settings = get_settings()
    with TestClient(main_module.app) as client:
        yield client

    reset_store()
    get_settings.cache_clear()


def headers(uid="demo-admin"):
    return {"Authorization": f"Bearer demo:{uid}"}


def create_dependency_chain(client, suffix):
    building = client.get("/api/v1/buildings", headers=headers()).json()[0]
    floor = client.post(
        "/api/v1/floors",
        headers=headers(),
        json={"building_id": building["id"], "name": f"Delete Floor {suffix}", "level": 50 + suffix, "description": "Deletion test"},
    ).json()
    shop = client.post(
        "/api/v1/shops",
        headers=headers(),
        json={"floor_id": floor["id"], "shop_number": f"DEL-{suffix}", "name": "Delete Shop", "monthly_rent": 12000, "status": "available"},
    ).json()
    tenant = client.post(
        "/api/v1/tenants",
        headers=headers(),
        json={"name": f"Delete Tenant {suffix}", "phone": "+8801700000000", "status": "active"},
    ).json()
    tenancy = client.post(
        "/api/v1/tenancies",
        headers=headers(),
        json={"tenant_id": tenant["id"], "shop_id": shop["id"], "start_date": "2026-08-01", "end_date": None, "monthly_rent": 12000, "security_deposit": 0, "status": "active"},
    ).json()
    return building, floor, shop, tenant, tenancy


def test_relationship_protections_and_atomic_tenancy_delete(deletion_client):
    client = deletion_client
    building, floor, shop, tenant, tenancy = create_dependency_chain(client, 1)

    building_delete = client.delete(f"/api/v1/buildings/{building['id']}", headers=headers())
    assert building_delete.status_code == 409
    assert "contains floors" in building_delete.json()["detail"]

    floor_delete = client.delete(f"/api/v1/floors/{floor['id']}", headers=headers())
    assert floor_delete.status_code == 409
    assert "contains shops" in floor_delete.json()["detail"]

    shop_delete = client.delete(f"/api/v1/shops/{shop['id']}", headers=headers())
    assert shop_delete.status_code == 409
    assert "currently occupied" in shop_delete.json()["detail"]

    tenant_delete = client.delete(f"/api/v1/tenants/{tenant['id']}", headers=headers())
    assert tenant_delete.status_code == 409
    assert "active tenancy" in tenant_delete.json()["detail"]

    forbidden = client.delete(f"/api/v1/floors/{floor['id']}", headers=headers("demo-accountant"))
    assert forbidden.status_code == 403
    assert client.delete("/api/v1/users/demo-accountant", headers=headers("demo-manager")).status_code == 403

    removed = client.delete(f"/api/v1/tenancies/{tenancy['id']}", headers=headers())
    assert removed.status_code == 200
    assert client.get(f"/api/v1/shops/{shop['id']}", headers=headers()).json()["status"] == "available"
    assert all(row["id"] != tenancy["id"] for row in client.get("/api/v1/tenancies", headers=headers()).json())

    assert client.delete(f"/api/v1/tenants/{tenant['id']}", headers=headers()).status_code == 200
    assert client.delete(f"/api/v1/shops/{shop['id']}", headers=headers()).status_code == 200
    assert client.delete(f"/api/v1/floors/{floor['id']}", headers=headers()).status_code == 200
    assert client.delete(f"/api/v1/floors/{floor['id']}", headers=headers()).status_code == 404


def test_financial_and_maintenance_records_can_be_deleted_and_replaced(deletion_client):
    client = deletion_client
    _, _, shop, _, tenancy = create_dependency_chain(client, 2)
    accountant = headers("demo-accountant")

    rent_payload = {"tenancy_id": tenancy["id"], "accounting_month": "2026-08", "amount": 12000, "payment_date": "2026-08-05", "status": "paid"}
    rent = client.post("/api/v1/rent-payments", headers=headers(), json=rent_payload).json()
    assert client.delete(f"/api/v1/rent-payments/{rent['id']}", headers=accountant).status_code == 200
    assert all(row["id"] != rent["id"] for row in client.get("/api/v1/rent-payments", headers=headers()).json())
    replacement_rent = client.post("/api/v1/rent-payments", headers=headers(), json=rent_payload)
    assert replacement_rent.status_code == 200

    utility_payload = {"shop_id": shop["id"], "tenancy_id": tenancy["id"], "utility_type": "water", "accounting_month": "2026-08", "amount": 800, "status": "unpaid"}
    utility = client.post("/api/v1/utility-bills", headers=headers(), json=utility_payload).json()
    assert client.delete(f"/api/v1/utility-bills/{utility['id']}", headers=accountant).status_code == 200
    assert client.post("/api/v1/utility-bills", headers=headers(), json=utility_payload).status_code == 200

    maintenance = client.post(
        "/api/v1/maintenance",
        headers=headers(),
        json={"scope_type": "shop", "scope_id": shop["id"], "maintenance_date": "2026-08-12", "description": "Replace a damaged lock", "cost": 500, "status": "completed"},
    ).json()
    assert client.delete(f"/api/v1/maintenance/{maintenance['id']}", headers=headers()).status_code == 200
    assert all(row["id"] != maintenance["id"] for row in client.get("/api/v1/maintenance", headers=headers()).json())

    protected_tenancy = client.delete(f"/api/v1/tenancies/{tenancy['id']}", headers=headers())
    assert protected_tenancy.status_code == 409
    assert "financial history" in protected_tenancy.json()["detail"]

    assert client.delete("/api/v1/rent-payments/missing-record", headers=accountant).status_code == 404


def test_user_delete_disables_firebase_account_and_removes_profile(monkeypatch):
    from app.api import users as users_api
    from app.core.auth import CurrentUser

    profiles = {
        "admin": {"id": "admin", "name": "Admin", "role": "administrator", "status": "active"},
        "manager": {"id": "manager", "name": "Manager", "role": "building_manager", "status": "active"},
    }

    class FakeStore:
        def get(self, collection, uid):
            return profiles.get(uid)

        def find(self, collection, **filters):
            return [record for record in profiles.values() if all(record.get(key) == value for key, value in filters.items())]

        def delete(self, collection, uid):
            return profiles.pop(uid, None) is not None

    class FakeAuth:
        def __init__(self):
            self.updates = []

        def update_user(self, uid, **changes):
            self.updates.append((uid, changes))

    auth_client = FakeAuth()
    monkeypatch.setattr(users_api, "get_store", lambda: FakeStore())
    monkeypatch.setattr(users_api, "get_settings", lambda: SimpleNamespace(auth_mode="firebase"))
    monkeypatch.setattr(users_api, "firebase_auth_client", lambda: auth_client)
    admin = CurrentUser(uid="admin", email="admin@brms.com", name="Admin", role="administrator")

    result = users_api.delete_user("manager", user=admin)
    assert result == {"deleted": True, "authentication_account": "disabled"}
    assert auth_client.updates == [("manager", {"disabled": True})]
    assert "manager" not in profiles

    with pytest.raises(HTTPException) as self_delete:
        users_api.delete_user("admin", user=admin)
    assert self_delete.value.status_code == 409


def test_last_active_administrator_cannot_be_deleted(monkeypatch):
    from app.api import users as users_api
    from app.core.auth import CurrentUser

    only_admin = {"id": "only-admin", "name": "Only Admin", "role": "administrator", "status": "active"}

    class FakeStore:
        def get(self, collection, uid):
            return only_admin if uid == "only-admin" else None

        def find(self, collection, **filters):
            return [only_admin]

    monkeypatch.setattr(users_api, "get_store", lambda: FakeStore())
    actor = CurrentUser(uid="provisioning-admin", email="admin@brms.com", name="Admin", role="administrator")

    with pytest.raises(HTTPException) as deletion:
        users_api.delete_user("only-admin", user=actor)
    assert deletion.value.status_code == 409
    assert "last active administrator" in deletion.value.detail
