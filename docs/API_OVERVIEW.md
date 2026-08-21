# API Overview

Base URL in local development: `http://127.0.0.1:8000/api/v1`

Every protected request includes:

```http
Authorization: Bearer <Firebase ID token>
```

Demo mode uses a local presentation token instead.

## Main endpoints

- `GET /system/health`
- `GET /auth/me`
- `GET /dashboard`
- `GET|POST|PATCH /buildings`
- `GET|POST|PATCH|DELETE /floors`
- `GET|POST|PATCH|DELETE /shops`
- `GET|POST|PATCH|DELETE /tenants`
- `GET|POST|PATCH /tenancies`
- `POST /tenancies/{id}/end`
- `GET|POST|PATCH|DELETE /rent-payments`
- `GET|POST|PATCH|DELETE /utility-bills`
- `GET|POST|PATCH|DELETE /maintenance`
- `GET /reports/monthly?month=YYYY-MM`
- `GET|POST|PATCH /users` (Administrator only)

FastAPI interactive documentation is available at `/docs` while the backend is running.
