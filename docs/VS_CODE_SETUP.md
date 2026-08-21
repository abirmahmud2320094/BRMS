# VS Code Local Setup

## First-time installation

From the project root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

Copy and configure the ignored environment files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Use Firebase Admin credentials only in `backend/.env`. Use the registered Firebase Web App values in `frontend/.env.local`.

## Normal startup

Open the repository in VS Code, open an integrated terminal at the project root, and run:

```bash
chmod +x scripts/start-real.sh
./scripts/start-real.sh
```

Open `http://localhost:5173` and sign in with an existing authorized Firebase account. The launcher reports a clear error when configuration, dependencies, credentials, connectivity, or ports are unavailable.

## Production deployment

Production uses Firebase Hosting for the React application and Render for the
FastAPI API at `https://brms-api-h2qf.onrender.com/api/v1`. From the repository
root, deploy a fresh Hosting-only build with:

```bash
./scripts/deploy-frontend.sh
```

The live frontend is `https://builing-rent-management-system.web.app`. The
script never deploys Firestore or Storage rules.

## Verification

```bash
cd backend
source .venv/bin/activate
pytest -q

cd ../frontend
npm test
npm run build
```
