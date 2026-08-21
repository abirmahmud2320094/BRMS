# Firebase Authentication and Firestore Setup

The normal BRMS application uses Firebase Authentication and Cloud Firestore through FastAPI.

## 1. Enable Firebase services

In Firebase Console:

1. Register a Web App under **Project settings → General**.
2. Enable **Authentication → Sign-in method → Email/Password**.
3. Create Cloud Firestore.
4. Keep the supplied Firestore rules deployed so browser clients cannot bypass FastAPI.

## 2. Configure the backend

Copy `backend/.env.example` to the ignored `backend/.env` and set:

```env
AUTH_MODE=firebase
DATA_MODE=firebase
FIREBASE_PROJECT_ID=your-firebase-project-id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/firebase-service-account.json
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

A deployment platform may provide `FIREBASE_SERVICE_ACCOUNT_JSON` as a secret instead. Never commit the JSON or place any service-account field in `frontend/`.

## 3. Configure the frontend

Copy `frontend/.env.example` to ignored `frontend/.env.local`. From the registered Web App configuration, set:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_FIREBASE_API_KEY=your-web-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-storage-bucket
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
```

Firebase Web SDK identifiers are public client configuration. Firebase Admin private keys, `client_email`, and service-account JSON are backend-only.

## 4. Authorized users

Each Firebase Authentication account must have a matching Firestore profile at `users/{firebase_uid}`:

```json
{
  "name": "Authorized User",
  "email": "user@example.com",
  "role": "building_manager",
  "status": "active"
}
```

Supported roles are `administrator`, `building_manager`, and `accountant`. An absent or inactive profile receives HTTP 403 from `/api/v1/auth/me`.

Manager and Accountant accounts can be provisioned idempotently with `backend/create_initial_users.py`; passwords must be supplied through ignored environment variables.

## 5. Start and verify

```bash
./scripts/start-real.sh
```

The launcher performs a real Firestore read and requires the backend health response to report Firebase authentication and Firebase data mode. Open `http://localhost:5173` and sign in with an existing authorized account.

Firebase persists the browser session. API requests obtain the current ID token through `currentUser.getIdToken()`; expired tokens are refreshed once after HTTP 401. Passwords and ID tokens are not manually stored by BRMS.
