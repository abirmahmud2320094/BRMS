import json
import logging
import os
import uuid
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)

COLLECTIONS = [
    "users",
    "buildings",
    "floors",
    "shops",
    "tenants",
    "tenancies",
    "rent_payments",
    "utility_bills",
    "maintenance_records",
]


class StoreError(RuntimeError):
    """Base exception for storage failures safe to map to an API response."""


class StoreConflict(StoreError):
    pass


class StoreNotFound(StoreError):
    pass


class StoreUnavailable(StoreError):
    pass


def _safe_firestore_failure_reason(exc: Exception) -> str:
    """Classify provider failures without logging credentials or request data."""
    chain = []
    current = exc
    while current is not None and len(chain) < 8:
        chain.append(f"{type(current).__name__} {current}".lower())
        current = current.__cause__ or current.__context__
    message = " ".join(chain)
    if "invalid jwt signature" in message or "invalid_grant" in message:
        return "firebase_admin_credentials_rejected"
    if "deadline exceeded" in message or "deadlineexceeded" in message:
        return "firestore_timeout"
    if "permission denied" in message or "permissiondenied" in message:
        return "firestore_permission_denied"
    if "unauthenticated" in message:
        return "firebase_admin_unauthenticated"
    if "unavailable" in message or "serviceunavailable" in message:
        return "firestore_unavailable"
    return "firestore_external_error"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _serialize(value: Any):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def _record(doc_id: str, value: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": doc_id, **_serialize(value)}


def _matches(record: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    return all(record.get(key) == value for key, value in filters.items())


class LocalJsonStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({name: {} for name in COLLECTIONS})

    def _read(self):
        with self.path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        for name in COLLECTIONS:
            data.setdefault(name, {})
        return data

    def _write(self, data):
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as file_handle:
            json.dump(_serialize(data), file_handle, ensure_ascii=False, indent=2)
        os.replace(temp, self.path)

    def _create_locked(self, data, collection, payload, doc_id=None):
        doc_id = doc_id or uuid.uuid4().hex[:20]
        if doc_id in data[collection]:
            raise StoreConflict(f"Document {collection}/{doc_id} already exists")
        now = _utc_now()
        record = _serialize(payload)
        record.setdefault("created_at", now)
        record.setdefault("updated_at", now)
        data[collection][doc_id] = record
        return _record(doc_id, deepcopy(record))

    def health_check(self):
        self._read()
        return True

    def list(self, collection: str) -> List[Dict[str, Any]]:
        with self.lock:
            data = self._read().get(collection, {})
            return [_record(key, deepcopy(value)) for key, value in data.items()]

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            value = self._read().get(collection, {}).get(doc_id)
            return _record(doc_id, deepcopy(value)) if value is not None else None

    def create(self, collection: str, payload: dict, doc_id: Optional[str] = None) -> dict:
        with self.lock:
            data = self._read()
            result = self._create_locked(data, collection, payload, doc_id)
            self._write(data)
            return result

    def create_unique(self, collection: str, payload: dict, unique_filters: dict, detail: str) -> dict:
        with self.lock:
            data = self._read()
            if any(_matches(item, unique_filters) for item in data[collection].values()):
                raise StoreConflict(detail)
            result = self._create_locked(data, collection, payload)
            self._write(data)
            return result

    def update(self, collection: str, doc_id: str, payload: dict) -> Optional[dict]:
        with self.lock:
            data = self._read()
            current = data.get(collection, {}).get(doc_id)
            if current is None:
                return None
            current.update(_serialize(payload))
            current["updated_at"] = _utc_now()
            self._write(data)
            return _record(doc_id, deepcopy(current))

    def update_unique(self, collection: str, doc_id: str, payload: dict, unique_filters: dict, detail: str) -> dict:
        with self.lock:
            data = self._read()
            current = data.get(collection, {}).get(doc_id)
            if current is None:
                raise StoreNotFound("Record not found")
            duplicate = any(
                other_id != doc_id and _matches(item, unique_filters)
                for other_id, item in data[collection].items()
            )
            if duplicate:
                raise StoreConflict(detail)
            current.update(_serialize(payload))
            current["updated_at"] = _utc_now()
            self._write(data)
            return _record(doc_id, deepcopy(current))

    def delete(self, collection: str, doc_id: str) -> bool:
        with self.lock:
            data = self._read()
            if doc_id not in data.get(collection, {}):
                return False
            del data[collection][doc_id]
            self._write(data)
            return True

    def find(self, collection: str, **filters) -> List[Dict[str, Any]]:
        return [record for record in self.list(collection) if _matches(record, filters)]

    def create_tenancy(self, payload: dict, doc_id: Optional[str] = None) -> dict:
        with self.lock:
            data = self._read()
            if payload["tenant_id"] not in data["tenants"]:
                raise StoreNotFound("Tenant not found")
            shop = data["shops"].get(payload["shop_id"])
            if shop is None:
                raise StoreNotFound("Shop not found")
            if payload.get("status") == "active":
                if shop.get("status") == "inactive":
                    raise StoreConflict("Inactive shop cannot receive a tenant assignment")
                active = any(
                    item.get("shop_id") == payload["shop_id"] and item.get("status") == "active"
                    for item in data["tenancies"].values()
                )
                if active:
                    raise StoreConflict("Shop already has an active tenant assignment")
            result = self._create_locked(data, "tenancies", payload, doc_id)
            if payload.get("status") == "active":
                shop["status"] = "occupied"
                shop["updated_at"] = _utc_now()
            self._write(data)
            return result

    def update_tenancy(self, doc_id: str, payload: dict) -> dict:
        with self.lock:
            data = self._read()
            current = data["tenancies"].get(doc_id)
            if current is None:
                raise StoreNotFound("Tenancy not found")
            if payload["tenant_id"] not in data["tenants"]:
                raise StoreNotFound("Tenant not found")
            new_shop = data["shops"].get(payload["shop_id"])
            if new_shop is None:
                raise StoreNotFound("Shop not found")
            if payload.get("status") == "active":
                if new_shop.get("status") == "inactive":
                    raise StoreConflict("Inactive shop cannot receive a tenant assignment")
                active = any(
                    other_id != doc_id
                    and item.get("shop_id") == payload["shop_id"]
                    and item.get("status") == "active"
                    for other_id, item in data["tenancies"].items()
                )
                if active:
                    raise StoreConflict("Shop already has an active tenant assignment")

            old_shop_id = current["shop_id"]
            current.update(_serialize(payload))
            current["updated_at"] = _utc_now()
            if old_shop_id != payload["shop_id"]:
                old_shop = data["shops"].get(old_shop_id)
                if old_shop:
                    old_shop["status"] = "available"
                    old_shop["updated_at"] = _utc_now()
            if payload.get("status") == "active":
                new_shop["status"] = "occupied"
                new_shop["updated_at"] = _utc_now()
            elif old_shop_id == payload["shop_id"]:
                new_shop["status"] = "available"
                new_shop["updated_at"] = _utc_now()
            self._write(data)
            return _record(doc_id, deepcopy(current))

    def end_tenancy(self, tenancy_id: str, end_date: str) -> dict:
        with self.lock:
            data = self._read()
            tenancy = data["tenancies"].get(tenancy_id)
            if tenancy is None:
                raise StoreNotFound("Tenancy not found")
            if tenancy.get("status") == "ended":
                return _record(tenancy_id, deepcopy(tenancy))
            tenancy.update({"status": "ended", "end_date": end_date, "updated_at": _utc_now()})
            shop = data["shops"].get(tenancy["shop_id"])
            if shop:
                shop.update({"status": "available", "updated_at": _utc_now()})
            self._write(data)
            return _record(tenancy_id, deepcopy(tenancy))

    def delete_tenancy(self, tenancy_id: str) -> bool:
        """Delete an assignment and release its shop as one local-store operation."""
        with self.lock:
            data = self._read()
            tenancy = data["tenancies"].get(tenancy_id)
            if tenancy is None:
                return False
            if tenancy.get("status") == "active":
                shop = data["shops"].get(tenancy.get("shop_id"))
                if shop:
                    shop.update({"status": "available", "updated_at": _utc_now()})
            del data["tenancies"][tenancy_id]
            self._write(data)
            return True


class FirestoreStore:
    def __init__(self):
        self.operation_timeout = get_settings().firebase_operation_timeout_seconds
        try:
            self.db = get_firestore_client()
        except Exception as exc:
            logger.error(
                "Cloud Firestore failure: operation=initialize reason=%s exception_type=%s",
                _safe_firestore_failure_reason(exc),
                type(exc).__name__,
            )
            raise StoreUnavailable(
                "Cloud Firestore initialization failed. Check FIREBASE_PROJECT_ID and Firebase Admin credentials."
            ) from exc

    def _run_transaction(self, operation):
        from firebase_admin import firestore

        return firestore.transactional(operation)(self.db.transaction())

    def _query(self, collection: str, filters: dict):
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.db.collection(collection)
        for key, value in filters.items():
            query = query.where(filter=FieldFilter(key, "==", value))
        return query

    def _transaction_document(self, transaction, reference):
        return next(
            transaction.get(reference, retry=None, timeout=self.operation_timeout),
            None,
        )

    def _document(self, snapshot) -> Dict[str, Any]:
        return _record(snapshot.id, snapshot.to_dict() or {})

    def _raise_operation_error(self, exc, operation: str = "operation"):
        if isinstance(exc, StoreError):
            raise exc
        logger.error(
            "Cloud Firestore failure: operation=%s reason=%s exception_type=%s",
            operation,
            _safe_firestore_failure_reason(exc),
            type(exc).__name__,
        )
        raise StoreUnavailable(
            "Cloud Firestore operation failed. Check connectivity, credentials, and required indexes."
        ) from exc

    def health_check(self):
        try:
            next(
                self.db.collection("users").limit(1).stream(
                    retry=None,
                    timeout=self.operation_timeout,
                ),
                None,
            )
            return True
        except Exception as exc:
            self._raise_operation_error(exc, "health_check")

    def list(self, collection: str) -> List[Dict[str, Any]]:
        try:
            return [
                self._document(doc)
                for doc in self.db.collection(collection).stream(
                    retry=None,
                    timeout=self.operation_timeout,
                )
            ]
        except Exception as exc:
            self._raise_operation_error(exc, f"list:{collection}")

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            snapshot = self.db.collection(collection).document(doc_id).get(
                retry=None,
                timeout=self.operation_timeout,
            )
            return self._document(snapshot) if snapshot.exists else None
        except Exception as exc:
            self._raise_operation_error(exc, f"get:{collection}")

    def create(self, collection: str, payload: dict, doc_id: Optional[str] = None) -> dict:
        try:
            from firebase_admin import firestore

            ref = self.db.collection(collection).document(doc_id) if doc_id else self.db.collection(collection).document()
            data = _serialize(payload)
            data.setdefault("created_at", firestore.SERVER_TIMESTAMP)
            data.setdefault("updated_at", firestore.SERVER_TIMESTAMP)
            ref.create(data, retry=None, timeout=self.operation_timeout)
            return self.get(collection, ref.id)
        except Exception as exc:
            self._raise_operation_error(exc, f"create:{collection}")

    def create_unique(self, collection: str, payload: dict, unique_filters: dict, detail: str) -> dict:
        ref = self.db.collection(collection).document()
        query = self._query(collection, unique_filters)

        def operation(transaction):
            if list(transaction.get(query, retry=None, timeout=self.operation_timeout)):
                raise StoreConflict(detail)
            from firebase_admin import firestore

            data = _serialize(payload)
            data.update({"created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
            transaction.create(ref, data)

        try:
            self._run_transaction(operation)
            return self.get(collection, ref.id)
        except Exception as exc:
            self._raise_operation_error(exc, f"create_unique:{collection}")

    def update(self, collection: str, doc_id: str, payload: dict) -> Optional[dict]:
        try:
            from firebase_admin import firestore

            ref = self.db.collection(collection).document(doc_id)
            if not ref.get(retry=None, timeout=self.operation_timeout).exists:
                return None
            ref.update(
                {**_serialize(payload), "updated_at": firestore.SERVER_TIMESTAMP},
                retry=None,
                timeout=self.operation_timeout,
            )
            return self.get(collection, doc_id)
        except Exception as exc:
            self._raise_operation_error(exc, f"update:{collection}")

    def update_unique(self, collection: str, doc_id: str, payload: dict, unique_filters: dict, detail: str) -> dict:
        ref = self.db.collection(collection).document(doc_id)
        query = self._query(collection, unique_filters)

        def operation(transaction):
            current = self._transaction_document(transaction, ref)
            duplicates = [
                snapshot
                for snapshot in transaction.get(
                    query,
                    retry=None,
                    timeout=self.operation_timeout,
                )
                if snapshot.id != doc_id
            ]
            if current is None or not current.exists:
                raise StoreNotFound("Record not found")
            if duplicates:
                raise StoreConflict(detail)
            from firebase_admin import firestore

            transaction.update(ref, {**_serialize(payload), "updated_at": firestore.SERVER_TIMESTAMP})

        try:
            self._run_transaction(operation)
            return self.get(collection, doc_id)
        except Exception as exc:
            self._raise_operation_error(exc, f"update_unique:{collection}")

    def delete(self, collection: str, doc_id: str) -> bool:
        try:
            ref = self.db.collection(collection).document(doc_id)
            if not ref.get(retry=None, timeout=self.operation_timeout).exists:
                return False
            ref.delete(retry=None, timeout=self.operation_timeout)
            return True
        except Exception as exc:
            self._raise_operation_error(exc, f"delete:{collection}")

    def find(self, collection: str, **filters) -> List[Dict[str, Any]]:
        try:
            return [
                self._document(doc)
                for doc in self._query(collection, filters).stream(
                    retry=None,
                    timeout=self.operation_timeout,
                )
            ]
        except Exception as exc:
            self._raise_operation_error(exc, f"find:{collection}")

    def create_tenancy(self, payload: dict, doc_id: Optional[str] = None) -> dict:
        tenancy_ref = self.db.collection("tenancies").document(doc_id) if doc_id else self.db.collection("tenancies").document()
        tenant_ref = self.db.collection("tenants").document(payload["tenant_id"])
        shop_ref = self.db.collection("shops").document(payload["shop_id"])
        active_query = self._query("tenancies", {"shop_id": payload["shop_id"], "status": "active"})

        def operation(transaction):
            tenant = self._transaction_document(transaction, tenant_ref)
            shop = self._transaction_document(transaction, shop_ref)
            active = (
                list(
                    transaction.get(
                        active_query,
                        retry=None,
                        timeout=self.operation_timeout,
                    )
                )
                if payload.get("status") == "active"
                else []
            )
            if tenant is None or not tenant.exists:
                raise StoreNotFound("Tenant not found")
            if shop is None or not shop.exists:
                raise StoreNotFound("Shop not found")
            if payload.get("status") == "active" and shop.to_dict().get("status") == "inactive":
                raise StoreConflict("Inactive shop cannot receive a tenant assignment")
            if active:
                raise StoreConflict("Shop already has an active tenant assignment")
            from firebase_admin import firestore

            data = {**_serialize(payload), "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP}
            transaction.create(tenancy_ref, data)
            if payload.get("status") == "active":
                transaction.update(shop_ref, {"status": "occupied", "updated_at": firestore.SERVER_TIMESTAMP})

        try:
            self._run_transaction(operation)
            return self.get("tenancies", tenancy_ref.id)
        except Exception as exc:
            self._raise_operation_error(exc, "create_tenancy")

    def update_tenancy(self, doc_id: str, payload: dict) -> dict:
        tenancy_ref = self.db.collection("tenancies").document(doc_id)
        tenant_ref = self.db.collection("tenants").document(payload["tenant_id"])
        new_shop_ref = self.db.collection("shops").document(payload["shop_id"])
        active_query = self._query("tenancies", {"shop_id": payload["shop_id"], "status": "active"})

        def operation(transaction):
            current_snapshot = self._transaction_document(transaction, tenancy_ref)
            tenant_snapshot = self._transaction_document(transaction, tenant_ref)
            new_shop_snapshot = self._transaction_document(transaction, new_shop_ref)
            active = (
                list(
                    transaction.get(
                        active_query,
                        retry=None,
                        timeout=self.operation_timeout,
                    )
                )
                if payload.get("status") == "active"
                else []
            )
            if current_snapshot is None or not current_snapshot.exists:
                raise StoreNotFound("Tenancy not found")
            if tenant_snapshot is None or not tenant_snapshot.exists:
                raise StoreNotFound("Tenant not found")
            if new_shop_snapshot is None or not new_shop_snapshot.exists:
                raise StoreNotFound("Shop not found")
            active = [snapshot for snapshot in active if snapshot.id != doc_id]
            if payload.get("status") == "active" and new_shop_snapshot.to_dict().get("status") == "inactive":
                raise StoreConflict("Inactive shop cannot receive a tenant assignment")
            if active:
                raise StoreConflict("Shop already has an active tenant assignment")

            from firebase_admin import firestore

            current = current_snapshot.to_dict()
            old_shop_id = current["shop_id"]
            old_shop_ref = self.db.collection("shops").document(old_shop_id)
            transaction.update(tenancy_ref, {**_serialize(payload), "updated_at": firestore.SERVER_TIMESTAMP})
            if old_shop_id != payload["shop_id"]:
                transaction.update(old_shop_ref, {"status": "available", "updated_at": firestore.SERVER_TIMESTAMP})
            if payload.get("status") == "active":
                transaction.update(new_shop_ref, {"status": "occupied", "updated_at": firestore.SERVER_TIMESTAMP})
            elif old_shop_id == payload["shop_id"]:
                transaction.update(new_shop_ref, {"status": "available", "updated_at": firestore.SERVER_TIMESTAMP})

        try:
            self._run_transaction(operation)
            return self.get("tenancies", doc_id)
        except Exception as exc:
            self._raise_operation_error(exc, "update_tenancy")

    def end_tenancy(self, tenancy_id: str, end_date: str) -> dict:
        tenancy_ref = self.db.collection("tenancies").document(tenancy_id)

        def operation(transaction):
            tenancy_snapshot = self._transaction_document(transaction, tenancy_ref)
            if tenancy_snapshot is None or not tenancy_snapshot.exists:
                raise StoreNotFound("Tenancy not found")
            tenancy = tenancy_snapshot.to_dict()
            if tenancy.get("status") == "ended":
                return
            shop_ref = self.db.collection("shops").document(tenancy["shop_id"])
            shop_snapshot = self._transaction_document(transaction, shop_ref)
            from firebase_admin import firestore

            transaction.update(
                tenancy_ref,
                {"status": "ended", "end_date": end_date, "updated_at": firestore.SERVER_TIMESTAMP},
            )
            if shop_snapshot is not None and shop_snapshot.exists:
                transaction.update(shop_ref, {"status": "available", "updated_at": firestore.SERVER_TIMESTAMP})

        try:
            self._run_transaction(operation)
            return self.get("tenancies", tenancy_id)
        except Exception as exc:
            self._raise_operation_error(exc, "end_tenancy")

    def delete_tenancy(self, tenancy_id: str) -> bool:
        """Delete an assignment and release an occupied shop in one transaction."""
        tenancy_ref = self.db.collection("tenancies").document(tenancy_id)

        def operation(transaction):
            tenancy_snapshot = self._transaction_document(transaction, tenancy_ref)
            if tenancy_snapshot is None or not tenancy_snapshot.exists:
                return False
            tenancy = tenancy_snapshot.to_dict()
            shop_ref = self.db.collection("shops").document(tenancy.get("shop_id"))
            shop_snapshot = self._transaction_document(transaction, shop_ref)

            transaction.delete(tenancy_ref)
            if tenancy.get("status") == "active" and shop_snapshot is not None and shop_snapshot.exists:
                from firebase_admin import firestore

                transaction.update(
                    shop_ref,
                    {"status": "available", "updated_at": firestore.SERVER_TIMESTAMP},
                )
            return True

        try:
            return bool(self._run_transaction(operation))
        except Exception as exc:
            self._raise_operation_error(exc, "delete_tenancy")


_store = None


def get_store():
    global _store
    if _store is None:
        settings = get_settings()
        mode = settings.data_mode.lower()
        if mode == "local":
            _store = LocalJsonStore(settings.local_data_path)
        elif mode == "firebase":
            _store = FirestoreStore()
        else:
            raise StoreUnavailable("DATA_MODE must be either 'local' or 'firebase'.")
    return _store


def reset_store():
    """Clear the cached store; intended for tests and explicit mode changes."""
    global _store
    _store = None
