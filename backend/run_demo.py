import os
os.environ.setdefault("AUTH_MODE", "demo")
os.environ.setdefault("DATA_MODE", "local")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
