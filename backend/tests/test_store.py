from datetime import datetime, timezone

import pytest

from app.services.store import FirestoreStore, LocalJsonStore, StoreConflict, StoreUnavailable


def make_local_store(tmp_path):
    store = LocalJsonStore(str(tmp_path / "local.json"))
    building = store.create("buildings", {"name": "Test", "address": "Dhaka"}, doc_id="building")
    floor = store.create("floors", {"building_id": building["id"], "name": "Ground", "level": 0}, doc_id="floor")
    shop = store.create(
        "shops",
        {"floor_id": floor["id"], "shop_number": "G-01", "monthly_rent": 1000, "status": "available"},
        doc_id="shop",
    )
    tenant = store.create(
        "tenants",
        {"name": "Test Tenant", "phone": "01700000000", "status": "active"},
        doc_id="tenant",
    )
    return store, shop, tenant


def test_local_store_enforces_unique_records(tmp_path):
    store, shop, tenant = make_local_store(tmp_path)
    payload = {"tenancy_id": "tenancy", "accounting_month": "2026-08", "amount": 1000}
    store.create_unique("rent_payments", payload, {"tenancy_id": "tenancy", "accounting_month": "2026-08"}, "duplicate")
    with pytest.raises(StoreConflict, match="duplicate"):
        store.create_unique("rent_payments", payload, {"tenancy_id": "tenancy", "accounting_month": "2026-08"}, "duplicate")


def test_tenancy_changes_shop_status_atomically(tmp_path):
    store, shop, tenant = make_local_store(tmp_path)
    tenancy = store.create_tenancy(
        {
            "tenant_id": tenant["id"],
            "shop_id": shop["id"],
            "start_date": "2026-08-01",
            "end_date": None,
            "monthly_rent": 1000,
            "security_deposit": 0,
            "status": "active",
            "notes": "",
        },
        doc_id="tenancy",
    )
    assert store.get("shops", shop["id"])["status"] == "occupied"

    with pytest.raises(StoreConflict, match="active tenant assignment"):
        store.create_tenancy({**tenancy, "tenant_id": tenant["id"], "shop_id": shop["id"]})

    ended = store.end_tenancy(tenancy["id"], "2026-08-31")
    assert ended["status"] == "ended"
    assert store.get("shops", shop["id"])["status"] == "available"


def test_demo_seed_is_idempotent(tmp_path, monkeypatch):
    from app.services import seed as seed_module

    store = LocalJsonStore(str(tmp_path / "seed.json"))
    monkeypatch.setattr(seed_module, "get_store", lambda: store)
    first = seed_module.seed_demo_data()
    counts_after_first = {collection: len(store.list(collection)) for collection in seed_module.COLLECTIONS}
    second = seed_module.seed_demo_data()
    counts_after_second = {collection: len(store.list(collection)) for collection in seed_module.COLLECTIONS}

    assert first["seeded"] is True
    assert second["seeded"] is False
    assert counts_after_first == counts_after_second
    assert counts_after_second["users"] == 3


class FakeSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = True

    def to_dict(self):
        return self._data


class FakeCollection:
    def __init__(self, snapshots=None, error=None):
        self.snapshots = snapshots or []
        self.error = error
        self.stream_kwargs = None

    def stream(self, **kwargs):
        self.stream_kwargs = kwargs
        if self.error:
            raise self.error
        return iter(self.snapshots)

    def limit(self, count):
        return self


class FakeFirestoreClient:
    def __init__(self, collection):
        self._collection = collection

    def collection(self, name):
        return self._collection


def test_firestore_records_are_json_safe():
    timestamp = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    store = object.__new__(FirestoreStore)
    collection = FakeCollection([FakeSnapshot("one", {"created_at": timestamp})])
    store.db = FakeFirestoreClient(collection)
    store.operation_timeout = 4.0
    assert store.list("users") == [{"id": "one", "created_at": "2026-08-20T12:00:00Z"}]
    assert collection.stream_kwargs == {"retry": None, "timeout": 4.0}


def test_firestore_connectivity_errors_are_sanitized(caplog):
    store = object.__new__(FirestoreStore)
    collection = FakeCollection(
        error=RuntimeError(
            "invalid_grant: Invalid JWT Signature. sensitive provider details"
        )
    )
    store.db = FakeFirestoreClient(collection)
    store.operation_timeout = 2.5
    with caplog.at_level("ERROR", logger="app.services.store"):
        with pytest.raises(StoreUnavailable, match="connectivity, credentials, and required indexes"):
            store.health_check()
    assert collection.stream_kwargs == {"retry": None, "timeout": 2.5}
    assert "operation=health_check" in caplog.text
    assert "reason=firebase_admin_credentials_rejected" in caplog.text
    assert "sensitive provider details" not in caplog.text


def test_firestore_transaction_document_unwraps_sdk_generator():
    snapshot = FakeSnapshot("one", {"status": "active"})

    class FakeTransaction:
        def get(self, reference, **kwargs):
            assert kwargs == {"retry": None, "timeout": 3.0}
            return iter([snapshot])

    store = object.__new__(FirestoreStore)
    store.operation_timeout = 3.0
    assert store._transaction_document(FakeTransaction(), object()) is snapshot
