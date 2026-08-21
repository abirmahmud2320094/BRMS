import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["AUTH_MODE"] = "demo"
os.environ["DATA_MODE"] = "local"
os.environ["LOCAL_DATA_PATH"] = str(ROOT / "backend" / "data" / "local_data.json")
from app.services.seed import seed_demo_data
print(seed_demo_data(force=True))
