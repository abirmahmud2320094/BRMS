# BRMS — Building Rental Management System

BRMS is a React, FastAPI, Firebase Authentication, and Cloud Firestore application for managing commercial buildings, shops, tenants, rent, utilities, maintenance, users, dashboards, and monthly reports.

## Architecture

```text
React + Vite
    ↓ Firebase email/password authentication
Firebase ID token
    ↓ Authorization: Bearer <token>
FastAPI validation and role enforcement
    ↓ Firebase Admin SDK
Cloud Firestore
```

BRMS roles are loaded from `users/{firebase_uid}` through `GET /api/v1/auth/me`. The frontend does not trust a role stored locally and does not access Firestore directly.

## Run the real local application

From the project root in the VS Code terminal:

```bash
chmod +x scripts/start-real.sh
./scripts/start-real.sh
```

Open `http://localhost:5173` and sign in with an authorized Firebase account. Public signup is intentionally unavailable; administrators manage BRMS users.

The launcher requires:

- `backend/.venv` with `backend/requirements.txt` installed
- `frontend/node_modules` with frontend dependencies installed
- ignored `backend/.env` configured for Firebase Admin
- ignored `frontend/.env.local` configured for the Firebase Web App
- ports 8000 and 5173 to be available

It verifies Firebase Admin credentials, Firestore connectivity, and `firebase/firebase` health modes before reporting readiness. It never falls back to local storage or legacy test authentication.

## First-time setup

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

Fill the two ignored environment files using [Firebase setup](docs/FIREBASE_SETUP.md). Never place service-account credentials in the frontend.

## Verification

```bash
cd backend
source .venv/bin/activate
pytest -q

cd ../frontend
npm test
npm run build
```

While running:

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/system/health`

The health response must report `"auth_mode": "firebase"` and `"data_mode": "firebase"`.

## Optional offline test fixtures

Backend automated tests retain isolated demo/local fixtures and seed utilities so tests do not require live Firebase credentials. They are not used by the normal real launcher or frontend authentication path.

See [Firebase setup](docs/FIREBASE_SETUP.md), [deployment preparation](docs/DEPLOYMENT.md), and the [user guide](docs/USER_GUIDE.md).
