from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api import auth, modules, dashboard, users, system
from app.services.seed import seed_demo_data
from app.services.store import StoreConflict, StoreError, StoreNotFound, StoreUnavailable, get_store

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auth_mode.lower() == "demo" and settings.data_mode.lower() == "local":
        seed_demo_data(force=False)
    else:
        get_store().health_check()
    yield


app = FastAPI(
    title="Building Rental Management System API",
    version="1.1.0",
    description="FastAPI backend for the BRMS academic project.",
    lifespan=lifespan,
)


@app.exception_handler(StoreConflict)
async def store_conflict_handler(request: Request, exc: StoreConflict):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(StoreNotFound)
async def store_not_found_handler(request: Request, exc: StoreNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(StoreUnavailable)
async def store_unavailable_handler(request: Request, exc: StoreUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(StoreError)
async def store_error_handler(request: Request, exc: StoreError):
    return JSONResponse(status_code=500, content={"detail": "Unexpected storage failure"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_v1_prefix
app.include_router(system.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(modules.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)


@app.get("/")
def root():
    return {"message":"BRMS API is running", "docs":"/docs", "health":f"{prefix}/system/health"}
