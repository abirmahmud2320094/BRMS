"""Seed presentation data in Cloud Firestore without creating Firebase Auth users."""
import argparse

from app.core.config import get_settings
from app.services.seed import seed_demo_data
from app.services.store import get_store


def main():
    parser = argparse.ArgumentParser(description="Seed BRMS demo profiles and linked business data in Firestore.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete BRMS collection documents before reseeding. Use only on a disposable/demo database.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.auth_mode.lower() != "demo" or settings.data_mode.lower() != "firebase":
        raise SystemExit("Set AUTH_MODE=demo and DATA_MODE=firebase before running this script.")

    get_store().health_check()
    result = seed_demo_data(force=args.reset)
    print("Firestore seed complete:", result)


if __name__ == "__main__":
    main()
