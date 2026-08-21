# Firestore Data Model

Core collections are aligned with the SRS:

- `users` — authorized BRMS profile and role, keyed by the corresponding Firebase Authentication UID.
- `buildings` — single Version 1 building profile.
- `floors` — references `building_id`.
- `shops` — references `floor_id`; status is `available`, `occupied`, or `inactive`.
- `tenants` — person/business identity and contact data.
- `tenancies` — references `tenant_id` and `shop_id`; active tenancy drives shop occupancy.
- `rent_payments` — references `tenancy_id` and one `YYYY-MM` accounting month.
- `utility_bills` — references `shop_id`, optional `tenancy_id`, utility type and accounting month.
- `maintenance_records` — building/floor/shop-scoped maintenance and expense data.

## Key rules enforced in FastAPI

1. A floor must reference the configured building.
2. A shop must reference a floor.
3. A shop cannot have more than one active tenancy.
4. Ending a tenancy releases its shop.
5. Duplicate monthly rent records for the same tenancy are rejected.
6. Duplicate utility-type records for the same shop/month are rejected.
7. Linked historical rental/billing data blocks unsafe hard deletion.
8. Demo tokens remain authenticated by FastAPI; user role/status is loaded from the server-side profile when present.

Firestore transactions protect active tenancy/shop occupancy changes and unique floor, shop, rent, and utility creation. The included composite indexes support those transactional queries.
