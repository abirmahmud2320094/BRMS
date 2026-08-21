"""Validate and import BRMS local JSON records into Cloud Firestore."""
import argparse
import json
from pathlib import Path
from typing import Dict

from pydantic import ValidationError

from app.core.config import get_settings
from app.models.schemas import (
    BuildingBase,
    FloorBase,
    MaintenanceBase,
    RentPaymentBase,
    ShopBase,
    TenantBase,
    TenancyBase,
    UserProfileBase,
    UtilityBillBase,
)
from app.services.store import COLLECTIONS, get_store


MODELS = {
    "users": UserProfileBase,
    "buildings": BuildingBase,
    "floors": FloorBase,
    "shops": ShopBase,
    "tenants": TenantBase,
    "tenancies": TenancyBase,
    "rent_payments": RentPaymentBase,
    "utility_bills": UtilityBillBase,
    "maintenance_records": MaintenanceBase,
}


def load_local_data(path: Path) -> Dict[str, dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Local data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Local data file is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("Local data root must be a JSON object")
    for collection in COLLECTIONS:
        if not isinstance(data.get(collection, {}), dict):
            raise ValueError(f"Collection '{collection}' must be a JSON object keyed by document ID")
        data.setdefault(collection, {})
    return data


def validate_local_data(data: Dict[str, dict]):
    errors = []
    metadata_fields = {"created_at", "updated_at", "created_by", "updated_by"}
    for collection, records in data.items():
        model = MODELS.get(collection)
        if not model:
            continue
        for doc_id, payload in records.items():
            try:
                model(**{key: value for key, value in payload.items() if key not in metadata_fields})
            except ValidationError as exc:
                errors.append(f"{collection}/{doc_id}: {exc.errors()[0]['msg']}")

    def require_reference(collection, doc_id, field, target_collection):
        target_id = data[collection][doc_id].get(field)
        if target_id and target_id not in data[target_collection]:
            errors.append(f"{collection}/{doc_id}: {field} references missing {target_collection}/{target_id}")

    for doc_id in data["floors"]:
        require_reference("floors", doc_id, "building_id", "buildings")
    for doc_id in data["shops"]:
        require_reference("shops", doc_id, "floor_id", "floors")
    for doc_id in data["tenancies"]:
        require_reference("tenancies", doc_id, "tenant_id", "tenants")
        require_reference("tenancies", doc_id, "shop_id", "shops")
    for doc_id in data["rent_payments"]:
        require_reference("rent_payments", doc_id, "tenancy_id", "tenancies")
    for doc_id in data["utility_bills"]:
        require_reference("utility_bills", doc_id, "shop_id", "shops")
        require_reference("utility_bills", doc_id, "tenancy_id", "tenancies")
    scope_collections = {"building": "buildings", "floor": "floors", "shop": "shops"}
    for doc_id, record in data["maintenance_records"].items():
        if record.get("scope_id"):
            require_reference(
                "maintenance_records",
                doc_id,
                "scope_id",
                scope_collections.get(record.get("scope_type"), "buildings"),
            )

    active_shops = set()
    for doc_id, tenancy in data["tenancies"].items():
        if tenancy.get("status") != "active":
            continue
        shop_id = tenancy.get("shop_id")
        if shop_id in active_shops:
            errors.append(f"tenancies/{doc_id}: shop {shop_id} has more than one active tenancy")
        active_shops.add(shop_id)
    for shop_id, shop in data["shops"].items():
        if shop_id in active_shops and shop.get("status") != "occupied":
            errors.append(f"shops/{shop_id}: active tenancy requires occupied status")
        if shop.get("status") == "occupied" and shop_id not in active_shops:
            errors.append(f"shops/{shop_id}: occupied status has no active tenancy")

    def check_duplicates(collection, fields):
        seen = set()
        for doc_id, payload in data[collection].items():
            key = tuple(payload.get(field) for field in fields)
            if key in seen:
                errors.append(f"{collection}/{doc_id}: duplicate unique key {fields}={key}")
            seen.add(key)

    check_duplicates("floors", ("building_id", "level"))
    check_duplicates("shops", ("floor_id", "shop_number"))
    check_duplicates("rent_payments", ("tenancy_id", "accounting_month"))
    check_duplicates("utility_bills", ("shop_id", "utility_type", "accounting_month"))

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:20])
        remaining = f"\n- ...and {len(errors) - 20} more" if len(errors) > 20 else ""
        raise ValueError(f"Local data validation failed:\n{preview}{remaining}")
    return True


def migrate(data: Dict[str, dict], overwrite: bool = False):
    store = get_store()
    store.health_check()
    result = {collection: {"created": 0, "updated": 0, "skipped": 0} for collection in COLLECTIONS}
    for collection in COLLECTIONS:
        for doc_id, payload in data[collection].items():
            existing = store.get(collection, doc_id)
            if existing and not overwrite:
                result[collection]["skipped"] += 1
            elif existing:
                store.update(collection, doc_id, payload)
                result[collection]["updated"] += 1
            else:
                store.create(collection, payload, doc_id=doc_id)
                result[collection]["created"] += 1
    return result


def main():
    parser = argparse.ArgumentParser(description="Migrate validated BRMS local JSON data to Firestore.")
    parser.add_argument("--source", default="data/local_data.json", help="Path to the local BRMS JSON file")
    parser.add_argument("--overwrite", action="store_true", help="Update Firestore documents with matching IDs")
    args = parser.parse_args()

    settings = get_settings()
    if settings.auth_mode.lower() != "demo" or settings.data_mode.lower() != "firebase":
        raise SystemExit("Set AUTH_MODE=demo and DATA_MODE=firebase before running this migration.")

    source = Path(args.source).expanduser().resolve()
    data = load_local_data(source)
    validate_local_data(data)
    result = migrate(data, overwrite=args.overwrite)
    print("Local-to-Firestore migration complete:")
    for collection, counts in result.items():
        print(f"  {collection}: {counts}")


if __name__ == "__main__":
    main()
