# Production Deployment

The production architecture is:

```text
Firebase Hosting → React/Vite → Firebase Authentication
                 → Render/FastAPI → Cloud Firestore
```

- Frontend: `https://builing-rent-management-system.web.app`
- Backend: `https://brms-api-h2qf.onrender.com`
- API base URL: `https://brms-api-h2qf.onrender.com/api/v1`

## Backend

Use Python 3.12 with:

- Root directory: `backend`
- Install: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Liveness health: `/api/v1/system/health`
- Firestore readiness: `/api/v1/system/readiness`

The liveness endpoint never performs a remote Firestore request, so platform
health checks remain responsive during a provider outage. The readiness
endpoint performs a timeout-bounded Firestore check when end-to-end storage
verification is needed.

Configure these as platform secrets/environment variables:

```env
AUTH_MODE=firebase
DATA_MODE=firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=<platform-secret>
FIREBASE_OPERATION_TIMEOUT_SECONDS=5
CORS_ORIGINS=https://your-project.web.app,https://your-project.firebaseapp.com
```

Never commit the service-account object or expose it through a `VITE_*` variable.

## Frontend

Create an ignored `frontend/.env.production` with the deployed API URL and registered Firebase Web App configuration:

```env
VITE_API_BASE_URL=https://your-api.example/api/v1
VITE_FIREBASE_API_KEY=your-web-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-storage-bucket
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
```

Then run `npm run build`. Firebase Web configuration is client-visible by design; Firebase Admin credentials remain server-only.

For a verified Hosting-only release, run from the project root:

```bash
./scripts/deploy-frontend.sh
```

The root `firebase.json` serves `frontend/dist` and rewrites all React routes to
`/index.html`. It retains Firestore and Storage configuration paths, but the
deployment helper uses `--only hosting` and does not redeploy their rules.

Render must explicitly allow both Firebase Hosting domains while preserving
the local development origins:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://builing-rent-management-system.web.app,https://builing-rent-management-system.firebaseapp.com
```

The Firebase Authentication authorized-domain list must include
`builing-rent-management-system.web.app`. Free Render instances can have a
noticeable cold start on the first request after inactivity; no artificial
keep-alive loop is required.

## Account provisioning

`backend/create_initial_users.py` creates or reuses Manager and Accountant Firebase Auth accounts and synchronizes their Firestore profiles. Provide temporary passwords only through ignored environment variables:

```env
BRMS_MANAGER_EMAIL=manager@brms.com
BRMS_MANAGER_PASSWORD=<temporary-manager-password>
BRMS_ACCOUNTANT_EMAIL=accountant@brms.com
BRMS_ACCOUNTANT_PASSWORD=<temporary-accountant-password>
FIREBASE_WEB_API_KEY=<firebase-web-api-key>
```

Run:

```bash
cd backend
source .venv/bin/activate
AUTH_MODE=firebase DATA_MODE=firebase python create_initial_users.py --verify
```

The script does not print passwords. Existing accounts are reused. Use `--update-existing-passwords` only for an intentional credential reset.
