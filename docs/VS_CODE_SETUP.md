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

## Verification

```bash
cd backend
source .venv/bin/activate
pytest -q

cd ../frontend
npm test
npm run build
```
