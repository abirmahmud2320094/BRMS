# Cloud Firestore Real Mode

BRMS uses this real local architecture:

```text
React/Vite → Firebase Authentication → Firebase ID token → FastAPI → Cloud Firestore
```

FastAPI remains responsible for validation, business rules, role authorization, reporting, and privileged Firestore access. The React application authenticates with Firebase but never reads or writes Firestore directly.

## Configuration

1. Follow [FIREBASE_SETUP.md](FIREBASE_SETUP.md).
2. Keep `AUTH_MODE=firebase` and `DATA_MODE=firebase` in ignored `backend/.env`.
3. Configure the registered Firebase Web App in ignored `frontend/.env.local`.
4. Ensure every authorized Firebase UID has a matching active `users/{uid}` profile.
5. Deploy the repository's Firestore rules and indexes when preparing the Firebase project.

## Start

From the repository root:

```bash
./scripts/start-real.sh
```

The launcher validates configuration, Firebase Admin credentials, Firestore connectivity, ports, process readiness, and the backend health modes. It does not reinstall dependencies and never falls back to demo/local mode.

The health response at `http://127.0.0.1:8000/api/v1/system/health` must contain:

```json
{
  "status": "ok",
  "auth_mode": "firebase",
  "data_mode": "firebase"
}
```

Open `http://localhost:5173` and sign in with an authorized Firebase email/password account.

## Data safety

Do not run destructive seed/reset commands against a database containing real BRMS records. Migration and legacy demo helpers are retained only for explicitly isolated development environments. Service-account files must remain outside the repository or under an ignored backend secrets path.
