import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_firebase_lifespan_does_not_touch_firestore(monkeypatch):
    from app import main as main_module
    from app.services import store as store_module

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(auth_mode="firebase", data_mode="firebase"),
    )

    def unexpected_store_access():
        raise AssertionError("Firestore must not be accessed during startup")

    monkeypatch.setattr(store_module, "get_store", unexpected_store_access)

    async def run_lifespan():
        async with main_module.lifespan(main_module.app):
            return True

    assert asyncio.run(asyncio.wait_for(run_lifespan(), timeout=0.25)) is True


def test_health_is_configuration_only(monkeypatch):
    from app.api import system

    settings = SimpleNamespace(
        app_name="BRMS API",
        app_env="test",
        auth_mode="firebase",
        data_mode="firebase",
    )
    monkeypatch.setattr(system, "get_settings", lambda: settings)
    monkeypatch.setattr(
        system,
        "get_store",
        lambda: (_ for _ in ()).throw(AssertionError("health must not access Firestore")),
    )

    result = system.health()
    assert result["status"] == "ok"
    assert result["storage_check"] == "lazy"


def test_readiness_sanitizes_store_failures(monkeypatch):
    from app.api import system
    from app.services.store import StoreUnavailable

    settings = SimpleNamespace(auth_mode="firebase", data_mode="firebase")

    class UnavailableStore:
        def health_check(self):
            raise StoreUnavailable("provider internals")

    monkeypatch.setattr(system, "get_settings", lambda: settings)
    monkeypatch.setattr(system, "get_store", lambda: UnavailableStore())

    with pytest.raises(HTTPException) as exc_info:
        system.readiness()
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "The configured data store is temporarily unavailable"


@pytest.mark.parametrize(
    "origin",
    [
        "https://builing-rent-management-system.web.app",
        "https://builing-rent-management-system.firebaseapp.com",
    ],
)
def test_production_hosting_origins_are_allowed(origin):
    from app.main import app

    client = TestClient(app)
    try:
        response = client.options(
            "/api/v1/system/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
    finally:
        client.close()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
