# Deployment Preparation

Public deployment is intentionally not performed by the local authentication migration.

## Backend

Use Python 3.12 with:

- Root directory: `backend`
- Install: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health: `/api/v1/system/health`

Configure these as platform secrets/environment variables:

```env
AUTH_MODE=firebase
DATA_MODE=firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=<platform-secret>
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
