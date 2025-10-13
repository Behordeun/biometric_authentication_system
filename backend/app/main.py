from contextlib import asynccontextmanager

from app.api.routes import auth, oidc
from app.core import auth as auth_core
from app.core.logging import get_logger
from app.db.database import Base, engine
from app.middleware.logging_middleware import LoggingMiddleware
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting application",
        additional_info={"action": "startup", "status": "starting"},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        logger.info(
            "Application started",
            additional_info={"action": "startup", "status": "success"},
        )
    except Exception as log_exc:
        # Optionally print or handle logging failure
        print(f"Failed to log application start: {log_exc}")
    yield


app = FastAPI(
    title="Hybrid Passwordless Authentication System",
    version="1.0.0",
    description="OAuth2, OpenID Connect, and WebAuthn (FIDO2) authentication",
    lifespan=lifespan,
)

# Configure CORS to allow all origins and methods (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(LoggingMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/")
async def root():
    return {
        "message": "Hybrid Passwordless Authentication System",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    try:
        # Check database
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/userinfo")
async def userinfo(current_user=Depends(auth_core.get_current_user)):
    try:
        return {
            "id": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
        }
    except Exception as exc:
        logger.error("Failed to retrieve user info", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to retrieve user info."},
            headers={"Access-Control-Allow-Origin": "*"},
        )


app.include_router(auth.router)
app.include_router(oidc.router)
